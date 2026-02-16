"""Open Food Facts API integration."""

import requests
import json

def fetch_product(barcode):
    """
    Fetch product data from Open Food Facts API.
    
    Args:
        barcode: Product barcode (EAN-13 or other)
    
    Returns:
        Product data dictionary or None if not found
    """
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 1:
            return normalize_product_data(data.get('product', {}))
        else:
            return None
    
    except Exception as e:
        print(f"Error fetching product: {e}")
        return None

def normalize_product_data(raw_product):
    """
    Normalize Open Food Facts data into our standard format.
    
    Args:
        raw_product: Raw product dictionary from API
    
    Returns:
        Normalized product dictionary
    """
    nutriments = raw_product.get('nutriments', {})
    
    # Extract additives
    additives = raw_product.get('additives_tags', [])
    additives_string = ','.join([a.replace('en:', '').upper() for a in additives])
    
    # Extract allergens
    allergens = raw_product.get('allergens_tags', [])
    allergens_string = ','.join([a.replace('en:', '').replace('-', ' ').title() for a in allergens])
    
    return {
        'barcode': raw_product.get('code', ''),
        'name': raw_product.get('product_name', 'Unknown Product'),
        'brand': raw_product.get('brands', 'Unknown Brand'),
        'image_url': raw_product.get('image_url', ''),
        
        # Scores
        'nutri_score': raw_product.get('nutriscore_grade', 'C').upper(),
        'nova_group': raw_product.get('nova_group', 3),
        'eco_score': raw_product.get('ecoscore_grade', 'C').upper(),
        
        # Nutrition per 100g
        'calories': nutriments.get('energy-kcal_100g', 0),
        'protein': nutriments.get('proteins_100g', 0),
        'carbs': nutriments.get('carbohydrates_100g', 0),
        'sugar': nutriments.get('sugars_100g', 0),
        'fat': nutriments.get('fat_100g', 0),
        'saturated_fat': nutriments.get('saturated-fat_100g', 0),
        'fiber': nutriments.get('fiber_100g', 0),
        'sodium': nutriments.get('sodium_100g', 0) * 1000,  # Convert to mg
        'salt': nutriments.get('salt_100g', 0),
        
        # Additional info
        'additives': additives_string,
        'allergens': allergens_string,
        'ingredients_text': raw_product.get('ingredients_text', ''),

        # Packaging (used for microplastics heuristic)
        'packaging': raw_product.get('packaging_text', raw_product.get('packaging', '')),
        'packaging_materials': ','.join(raw_product.get('packaging_materials_tags', []) or []),
        
        # Dietary labels
        'vegan': 1 if 'en:vegan' in raw_product.get('labels_tags', []) else 0,
        'vegetarian': 1 if 'en:vegetarian' in raw_product.get('labels_tags', []) else 0,
        'organic': 1 if 'en:organic' in raw_product.get('labels_tags', []) else 0,
        'gluten_free': 1 if 'en:gluten-free' in raw_product.get('labels_tags', []) else 0,
        
        # Categories
        'categories': raw_product.get('categories', ''),
        
        # Serving size
        'serving_size': raw_product.get('serving_size', ''),
        'serving_quantity': raw_product.get('serving_quantity', 100),
    }

def search_products(query, page=1, page_size=20):
    """
    Search for products by name.
    
    Args:
        query: Search query string
        page: Page number (1-indexed)
        page_size: Number of results per page
    
    Returns:
        List of product dictionaries
    """
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    
    params = {
        'search_terms': query,
        'page': page,
        'page_size': page_size,
        'json': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        products = []
        for raw_product in data.get('products', []):
            try:
                products.append(normalize_product_data(raw_product))
            except Exception as e:
                print(f"Error normalizing product: {e}")
                continue
        
        return products
    
    except Exception as e:
        print(f"Error searching products: {e}")
        return []

def get_sample_products():
    """
    Get sample products for demo purposes.
    
    Returns:
        List of sample product dictionaries
    """
    samples = [
        {
            'barcode': '3017620422003',
            'name': 'Nutella',
            'brand': 'Ferrero',
            'nutri_score': 'E',
            'nova_group': 4,
            'eco_score': 'D',
            'calories': 539,
            'protein': 6.3,
            'carbs': 57.5,
            'sugar': 56.3,
            'fat': 30.9,
            'saturated_fat': 10.6,
            'fiber': 0,
            'sodium': 107,
            'additives': 'E322,E476',
            'allergens': 'nuts,milk',
            'vegan': 0,
            'vegetarian': 1
        },
        {
            'barcode': '5449000000996',
            'name': 'Coca-Cola',
            'brand': 'Coca-Cola',
            'nutri_score': 'E',
            'nova_group': 4,
            'eco_score': 'C',
            'calories': 42,
            'protein': 0,
            'carbs': 10.6,
            'sugar': 10.6,
            'fat': 0,
            'saturated_fat': 0,
            'fiber': 0,
            'sodium': 11,
            'additives': 'E150d,E338',
            'allergens': '',
            'vegan': 1,
            'vegetarian': 1
        },
        {
            'barcode': '8076800195057',
            'name': 'Organic Whole Wheat Pasta',
            'brand': 'Barilla',
            'nutri_score': 'A',
            'nova_group': 1,
            'eco_score': 'B',
            'calories': 348,
            'protein': 13,
            'carbs': 70.2,
            'sugar': 3.2,
            'fat': 2.7,
            'saturated_fat': 0.5,
            'fiber': 8.5,
            'sodium': 6,
            'additives': '',
            'allergens': 'gluten',
            'vegan': 1,
            'vegetarian': 1
        }
    ]
    
    return samples
