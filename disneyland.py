import requests
import json
from datetime import datetime, timedelta
import uuid
import os
import logging
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify
import threading
from config import get_config

class DisneylandMenuFetcher:
    def __init__(self, config=None, debug=False):
        self.config = config or get_config()
        self.base_url = self.config.BASE_URL
        self.session = requests.Session()
        self.conversation_uuid = str(uuid.uuid4())
        self.debug = debug or self.config.DEBUG
        
        # Set up logging
        self._setup_logging()
        
        # Create output directory if it doesn't exist (skip if read-only)
        self.output_dir = self.config.CACHE_DIR
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except PermissionError:
            self.logger.info(f"Cannot create cache directory {self.output_dir} (read-only filesystem)")
            # Directory might already exist from repo, check if we can read from it
            if not os.path.exists(self.output_dir):
                self.logger.warning(f"Cache directory {self.output_dir} does not exist and cannot be created")
        
        # Set up base headers that will be used for all requests
        self.base_headers = self.config.get_headers()
        self.base_headers["Undefined"] = self.conversation_uuid
        
        # Clean up old cache files on initialization (only if auto-cleanup is enabled)
        if self.config.CACHE_AUTO_CLEANUP:
            self.cleanup_old_cache_files(self.config.CACHE_CLEANUP_DAYS)
        
        self.logger.info(f"DisneylandMenuFetcher initialized with date: {self.config.API_DATE}")
    
    def _setup_logging(self):
        """Set up logging configuration"""
        log_level = getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO)
        
        # Configure logger
        self.logger = logging.getLogger('DisneylandMenu')
        self.logger.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if configured
        if self.config.LOG_FILE:
            file_handler = logging.FileHandler(self.config.LOG_FILE)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def save_response(self, response, filename):
        """Save response data to a JSON file (optional in read-only environments)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.output_dir, f"{filename}_{timestamp}.json")
        
        try:
            data = response.json()
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            if self.debug:
                self.logger.info(f"Saved response to {filepath}")
        except PermissionError:
            if self.debug:
                self.logger.info(f"Cannot write to {filepath} (read-only filesystem)")
        except Exception as e:
            self.logger.warning(f"Error saving response to {filepath}: {e}")

    def debug_request(self, response):
        """Print debug information about a request."""
        if self.debug:
            print("\n=== REQUEST ===")
            print(f"URL: {response.request.url}")
            print(f"Method: {response.request.method}")
            print("\nHeaders:")
            for header, value in response.request.headers.items():
                print(f"{header}: {value}")
            print("\nBody:")
            print(response.request.body or "{}")
            print("\n=== RESPONSE ===")
            print(f"Status: {response.status_code}")
            print("\nHeaders:")
            for header, value in response.headers.items():
                print(f"{header}: {value}")
            print("\nCookies:")
            for cookie in self.session.cookies:
                print(f"{cookie.name}: {cookie.value}")
            print("\nResponse Body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text[:1000])
            print("="*80)

    def get_auth_token(self) -> str:
        """Step 1: Get authentication token from authz endpoint."""
        try:
            response = self.session.post(
                f"{self.base_url}/finder/api/v1/authz/public",
                headers=self.base_headers,
                json={}
            )
            response.raise_for_status()
            
            # Save auth response
            self.save_response(response, "auth_response")
            
            if self.debug:
                self.debug_request(response)
            
            if "__d" in self.session.cookies:
                return self.session.cookies["__d"]
            
            print("Failed to get authentication token")
            return None
        except requests.RequestException as e:
            print(f"Error getting auth token: {e}")
            return None

    def _get_most_recent_menu_file(self, url_friendly_id: str, date: str = None) -> Optional[str]:
        """Find the most recent menu response file for a restaurant."""
        date = date or self.config.API_DATE
        
        if not os.path.exists(self.output_dir):
            return None
            
        # First try with specific date (prioritize GitHub Action cached files)
        prefix = f"menu_response_{url_friendly_id}_{date}_"
        matching_files = [f for f in os.listdir(self.output_dir) if f.startswith(prefix) and f.endswith('.json')]
        
        # If no date-specific files, try without date for backward compatibility
        if not matching_files:
            prefix = f"menu_response_{url_friendly_id}_"
            matching_files = [f for f in os.listdir(self.output_dir) if f.startswith(prefix) and f.endswith('.json')]
            
        if not matching_files:
            return None
            
        # Get the most recent file
        most_recent = max(matching_files, key=lambda x: os.path.getmtime(os.path.join(self.output_dir, x)))
        return os.path.join(self.output_dir, most_recent)

    def _is_file_recent(self, filepath: str, hours: int = None) -> bool:
        """Check if a file is more recent than the specified number of hours."""
        if not self.config.CACHE_ENABLED:
            return False
            
        if not os.path.exists(filepath):
            return False
        
        # If we're in a read-only environment (like Render), treat existing files as always recent
        # This allows us to use pre-committed files from GitHub Actions
        try:
            # Test if we can write to the cache directory
            test_file = os.path.join(self.output_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            # If we can write, use normal cache timing
            hours = hours or self.config.CACHE_HOURS
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            age = datetime.now() - file_mtime
            return age.total_seconds() < hours * 3600
        except (PermissionError, OSError):
            # Read-only filesystem - use any existing files
            self.logger.info(f"Using pre-cached file in read-only environment: {filepath}")
            return True
    
    def _get_cached_restaurants_file(self, date: str = None) -> Optional[str]:
        """Find the most recent extracted restaurants file for a specific date."""
        date = date or self.config.API_DATE
        prefix = f"extracted_restaurants_{date}_"
        
        if not os.path.exists(self.output_dir):
            return None
            
        matching_files = [f for f in os.listdir(self.output_dir) if f.startswith(prefix) and f.endswith('.json')]
        if not matching_files:
            return None
            
        # Get the most recent file
        most_recent = max(matching_files, key=lambda x: os.path.getmtime(os.path.join(self.output_dir, x)))
        return os.path.join(self.output_dir, most_recent)
    
    def _load_cached_restaurants(self, date: str = None) -> Optional[list]:
        """Load cached restaurant data if available and recent."""
        cached_file = self._get_cached_restaurants_file(date)
        if cached_file and self._is_file_recent(cached_file):
            try:
                self.logger.info(f"Loading cached restaurant data from {cached_file}")
                with open(cached_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error reading cached restaurants: {e}")
        return None
    
    def get_cache_last_updated(self) -> Optional[datetime]:
        """Get the timestamp of the most recent cache file."""
        if not os.path.exists(self.output_dir):
            return None
            
        try:
            cache_files = [f for f in os.listdir(self.output_dir) 
                          if f.endswith('.json') and not f.startswith('.')]
            if not cache_files:
                return None
                
            # Get the most recently modified cache file
            most_recent_file = max(cache_files, 
                                 key=lambda x: os.path.getmtime(os.path.join(self.output_dir, x)))
            most_recent_path = os.path.join(self.output_dir, most_recent_file)
            return datetime.fromtimestamp(os.path.getmtime(most_recent_path))
        except Exception as e:
            self.logger.warning(f"Error getting cache timestamp: {e}")
            return None
    
    def cleanup_old_cache_files(self, days_to_keep: int = 7):
        """Remove cache files older than specified days."""
        if not os.path.exists(self.output_dir):
            return
            
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        try:
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
                        self.logger.debug(f"Removed old cache file: {filename}")
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old cache files older than {days_to_keep} days")
        except Exception as e:
            self.logger.warning(f"Error cleaning up cache files: {e}")

    def fetch_menu(self, url_friendly_id: str, restaurant_name: str, location_name: str, date: str = None) -> List[Dict]:
        """Fetch menu items for a specific restaurant."""
        date = date or self.config.API_DATE
        # Check for recent cached response
        cached_file = self._get_most_recent_menu_file(url_friendly_id, date)
        if cached_file and self._is_file_recent(cached_file):
            if self.debug:
                print(f"Using cached menu for {restaurant_name} from {cached_file}")
            try:
                with open(cached_file, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                if self.debug:
                    print(f"Error reading cached menu: {e}")
                data = None
        else:
            try:
                url = f"{self.base_url}/dining/dinemenu/api/menu"
                params = {
                    'searchTerm': url_friendly_id,
                    'language': 'en-us'
                }
                
                response = self.session.get(url, headers=self.base_headers, params=params)
                response.raise_for_status()
                
                # Save menu response with date
                self.save_response(response, f"menu_response_{url_friendly_id}_{date}")
                
                if self.debug:
                    self.debug_request(response)
                
                data = response.json()
            except requests.RequestException as e:
                if self.debug:
                    print(f"Error fetching menu for {restaurant_name}: {e}")
                return []
            except json.JSONDecodeError as e:
                if self.debug:
                    print(f"Error parsing menu data for {restaurant_name}: {e}")
                return []
            except Exception as e:
                if self.debug:
                    print(f"Unexpected error fetching menu for {restaurant_name}: {e}")
                return []

        menu_items = []
        if not data:
            return menu_items

        # Process menu data - handle both mealPeriods and menus structures
        meal_periods = data.get('mealPeriods', [])
        
        for period in meal_periods:
            period_name = period.get('name', 'Unknown')
            for group in period.get('groups', []):
                for item in group.get('items', []):
                    # Safely handle price extraction
                    prices = item.get('prices', [])
                    price = 'N/A'
                    if prices and len(prices) > 0:
                        price = prices[0].get('withoutTax', 'N/A')
                    
                    menu_item = {
                        'name': item.get('title', 'Unknown'),
                        'restaurant_name': restaurant_name,
                        'cost': f"${price}" if price != 'N/A' else 'N/A',
                        'land': location_name,
                        'time_till_close': period_name,  # Using meal period name instead
                        'description': item.get('description', ''),
                        'category': group.get('name', 'Unknown')
                    }
                    menu_items.append(menu_item)
        
        return menu_items

    def fetch_restaurants(self, date: str = None) -> list:
        """Step 2: Get list of restaurants."""
        # Use provided date or default from config
        api_date = date or self.config.API_DATE
        
        # Check for cached restaurant data first
        cached_restaurants = self._load_cached_restaurants(api_date)
        if cached_restaurants:
            self.logger.info(f"Using cached restaurant data for {api_date} ({len(cached_restaurants)} restaurants)")
            return cached_restaurants
        
        self.logger.info(f"Fetching fresh restaurant data for {api_date}")
        
        # First get auth token
        token = self.get_auth_token()
        if not token:
            self.logger.error("Failed to authenticate")
            return []

        # Update headers with auth token
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {token}"
        
        try:
            url = f"{self.base_url}/finder/api/v1/explorer-service/list-ancestor-entities/dlr/80008297;entityType=destination/{api_date}/dining"
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            # Save restaurants response
            self.save_response(response, "restaurants_response")
            
            if self.debug:
                self.debug_request(response)
            
            data = response.json()
            
            # Step 3: Parse and extract restaurant information
            restaurants = []
            seen_ids = set()  # Track unique restaurant IDs
            
            for entity in data.get('results', []):
                # Get basic information
                restaurant_info = {
                    'id': entity.get('id', ''),
                    'name': entity.get('name', 'Unknown'),
                    'url': entity.get('url', ''),
                    'url_friendly_id': entity.get('urlFriendlyId', ''),
                    'location_name': entity.get('locationName', ''),
                    'entity_type': entity.get('entityType', ''),
                    'maximum_party_size': entity.get('maximumPartySize', ''),
                    'quick_service': entity.get('quickServiceAvailable', False),
                    'facility_id': entity.get('facilityId', ''),
                    'price_range': entity.get('facets', {}).get('priceRange', []),
                    'cuisine_types': entity.get('facets', {}).get('cuisine', []),
                    'dining_types': entity.get('facets', {}).get('tableService', []),
                    'coordinates': [],
                    'additional_info': entity.get('generalPurposeStrings', {}).get('diningAdditionalInfo', ''),
                    'product_urls': entity.get('productUrls', []),
                    'media': {},
                    'menu_items': []  # New field to store menu items
                }
                
                # Extract media information if available
                if 'media' in entity:
                    media = entity['media']
                    if 'finderStandardThumb' in media:
                        restaurant_info['media']['thumbnail'] = {
                            'url': media['finderStandardThumb'].get('url', ''),
                            'alt': media['finderStandardThumb'].get('alt', '')
                        }
                
                # Extract coordinates from all associated restaurants
                for rest in entity.get('restaurants', []):
                    if 'coordinates' in rest:
                        for entrance, coord in rest['coordinates'].items():
                            if 'gps' in coord:
                                restaurant_info['coordinates'].append({
                                    'entrance': entrance,
                                    'latitude': coord['gps'].get('latitude', ''),
                                    'longitude': coord['gps'].get('longitude', '')
                                })
                
                # Fetch menu items if we have a URL friendly ID
                if restaurant_info['url_friendly_id']:
                    restaurant_info['menu_items'] = self.fetch_menu(
                        restaurant_info['url_friendly_id'],
                        restaurant_info['name'],
                        restaurant_info['location_name'],
                        api_date
                    )
                
                # Check if we've already seen this restaurant
                if restaurant_info['id'] and restaurant_info['id'] not in seen_ids:
                    seen_ids.add(restaurant_info['id'])
                    restaurants.append(restaurant_info)
                
                # Also check marker information for additional restaurants
                marker = entity.get('marker', {})
                if marker:
                    marker_info = {
                        'id': marker.get('id', ''),
                        'name': marker.get('name', 'Unknown'),
                        'url': marker.get('url', ''),
                        'url_friendly_id': marker.get('urlFriendlyId', ''),
                        'location_name': entity.get('locationName', ''),
                        'entity_type': 'restaurant',
                        'coordinates': [],
                        'menu_items': []  # New field to store menu items
                    }
                    
                    # Add coordinates if available
                    if 'lat' in marker and 'lng' in marker:
                        marker_info['coordinates'].append({
                            'entrance': 'Main',
                            'latitude': str(marker.get('lat', '')),
                            'longitude': str(marker.get('lng', ''))
                        })
                    
                    # Fetch menu items if we have a URL friendly ID
                    if marker_info['url_friendly_id']:
                        marker_info['menu_items'] = self.fetch_menu(
                            marker_info['url_friendly_id'],
                            marker_info['name'],
                            marker_info['location_name'],
                            api_date
                        )
                    
                    # Check if we've already seen this restaurant
                    if marker_info['id'] and marker_info['id'] not in seen_ids:
                        seen_ids.add(marker_info['id'])
                        restaurants.append(marker_info)
            
            # Save extracted restaurant data with date
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.output_dir, f"extracted_restaurants_{api_date}_{timestamp}.json")
            with open(filepath, 'w') as f:
                json.dump(restaurants, f, indent=2)
            
            return restaurants
            
        except requests.RequestException as e:
            print(f"Error fetching restaurants: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing restaurant data: {e}")
            return []

def create_app(fetcher=None):
    app = Flask(__name__)
    config = get_config()
    app.config.from_object(config)
    
    if fetcher is None:
        fetcher = DisneylandMenuFetcher(config=config)
    
    # Store fetcher in app context
    app.fetcher = fetcher
    
    @app.route('/')
    def index():
        try:
            tab = request.args.get('tab', 'food')
            # Get date from query params or use default
            selected_date = request.args.get('date', config.API_DATE)
            
            # Validate date is within allowed range
            from datetime import datetime, timedelta
            try:
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                max_date = today + timedelta(days=config.MAX_DAYS_AHEAD)
                
                if date_obj < today or date_obj > max_date:
                    selected_date = config.API_DATE
                    date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
            except ValueError:
                selected_date = config.API_DATE
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
            
            restaurants = fetcher.fetch_restaurants(date=selected_date)
            
            # Generate available dates for selector
            available_dates = []
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for i in range(config.MAX_DAYS_AHEAD + 1):
                date = today + timedelta(days=i)
                available_dates.append({
                    'value': date.strftime('%Y-%m-%d'),
                    'display': 'Today' if i == 0 else 'Tomorrow' if i == 1 else date.strftime('%a %b %d')
                })
            
            # Get all menu items and locations
            all_menu_items = []
            locations = set()
            
            for restaurant in restaurants:
                for item in restaurant.get('menu_items', []):
                    locations.add(item['land'])
                    # Determine if item is beverage based on category
                    is_beverage = any(beverage_keyword in item['category'].lower() 
                                    for beverage_keyword in ['beverage', 'drink', 'beer', 'wine', 'cocktail'])
                    
                    if (tab == 'beverages' and is_beverage) or (tab == 'food' and not is_beverage):
                        all_menu_items.append(item)
            
            # Get cache last updated time
            last_updated = fetcher.get_cache_last_updated()
            
            return render_template('index.html',
                                 menu_items=all_menu_items,
                                 locations=sorted(list(locations)),
                                 active_tab=tab,
                                 selected_date=selected_date,
                                 available_dates=available_dates,
                                 show_refresh=config.ENABLE_REFRESH_BUTTON,
                                 enable_favorites=config.ENABLE_FAVORITES,
                                 enable_date_selector=config.ENABLE_DATE_SELECTOR,
                                 last_updated=last_updated)
        except Exception as e:
            fetcher.logger.error(f"Error loading menu data: {e}")
            return render_template('error.html', error=str(e)), 500
    
    @app.route('/api/refresh', methods=['POST'])
    def refresh_data():
        """Force refresh of cached data"""
        if not config.ENABLE_REFRESH_BUTTON:
            return jsonify({'error': 'Refresh disabled'}), 403
        
        try:
            # Get date from request
            data = request.get_json() or {}
            date = data.get('date', config.API_DATE)
            
            # Only clear cache for the specific date
            if os.path.exists(fetcher.output_dir):
                # Remove files for this specific date
                for filename in os.listdir(fetcher.output_dir):
                    if date in filename:
                        os.remove(os.path.join(fetcher.output_dir, filename))
            
            # Fetch fresh data for the date
            restaurants = fetcher.fetch_restaurants(date=date)
            return jsonify({
                'success': True, 
                'message': f'Refreshed data for {len(restaurants)} restaurants on {date}',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            fetcher.logger.error(f"Error refreshing data: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/status')
    def status():
        """Get app status and configuration info"""
        last_updated = fetcher.get_cache_last_updated()
        return jsonify({
            'status': 'healthy',
            'config': {
                'api_date': config.API_DATE,
                'cache_enabled': config.CACHE_ENABLED,
                'cache_hours': config.CACHE_HOURS,
                'cache_cleanup_days': config.CACHE_CLEANUP_DAYS,
                'refresh_enabled': config.ENABLE_REFRESH_BUTTON
            },
            'cache_last_updated': last_updated.isoformat() if last_updated else None,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/cleanup-cache', methods=['POST'])
    def cleanup_cache():
        """Manually trigger cache cleanup"""
        try:
            days_to_keep = request.json.get('days', config.CACHE_CLEANUP_DAYS) if request.json else config.CACHE_CLEANUP_DAYS
            fetcher.cleanup_old_cache_files(days_to_keep)
            return jsonify({
                'success': True,
                'message': f'Cache cleanup completed for files older than {days_to_keep} days',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            fetcher.logger.error(f"Error during cache cleanup: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('error.html', error='Internal server error'), 500

    return app

def main():
    import argparse
    # Load environment variables from .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed or .env not present
    
    parser = argparse.ArgumentParser(description='Fetch Disneyland restaurant URLs')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--web', action='store_true', help='Run as web service')
    parser.add_argument('--date', help='Date for API queries (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # Get configuration
    config = get_config()
    
    # Override date if provided
    if args.date:
        config.API_DATE = args.date
    
    fetcher = DisneylandMenuFetcher(config=config, debug=args.debug)
    
    if args.web:
        # Create templates directory if it doesn't exist
        os.makedirs('templates', exist_ok=True)
        
        # Create and run the Flask app
        app = create_app(fetcher)
        app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
        return
    
    print("Fetching restaurant information...")
    
    restaurants = fetcher.fetch_restaurants()
    if not restaurants:
        print("No restaurants found")
        return
    
    print(f"\nFound {len(restaurants)} restaurants")
    
    # Print header
    print("\nMenuItem | Restaurant Name | Cost | Land | Time till close")
    print("-" * 100)
    
    # Print all menu items
    total_items = 0
    for restaurant in restaurants:
        menu_items = restaurant.get('menu_items', [])
        if menu_items:
            total_items += len(menu_items)
            for menu_item in menu_items:
                print(f"{menu_item['name'][:35]:35} | "
                      f"{menu_item['restaurant_name'][:25]:25} | "
                      f"{str(menu_item['cost']):8} | "
                      f"{menu_item['land'][:20]:20} | "
                      f"{menu_item['time_till_close']}")
    
    print(f"\nFound {total_items} menu items across {len(restaurants)} restaurants")
    print(f"\nDetailed responses have been saved to the '{fetcher.output_dir}' directory")

if __name__ == "__main__":
    main()
