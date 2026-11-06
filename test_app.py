"""
Unit and Integration Smoke Tests for AgriMitra AI Flask backend
"""
import unittest
import json
from app import app

class TestAgriMitraAI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AgriMitra AI', response.data)

    def test_meta_endpoint(self):
        response = self.app.get('/api/meta')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['commodities']) > 0)
        self.assertTrue('Wheat' in data['commodities'])

    def test_weather_endpoint(self):
        response = self.app.get('/api/weather?lat=19.7515&lon=75.7139&name=Maharashtra')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('current', data)
        self.assertIn('climate_intelligence', data)
        self.assertTrue(len(data['forecast_7day']) >= 7)

    def test_mandi_prices_endpoint(self):
        response = self.app.get('/api/mandi/prices?crop=Soyabean&state=all')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['data']) > 0)
        self.assertIn('modal_price', data['data'][0])
        self.assertIn('msp', data['data'][0])

    def test_arbitrage_recommendation(self):
        payload = {
            "farmer_lat": 19.9975,
            "farmer_lon": 73.7898,
            "farmer_location_name": "Nashik",
            "crop": "Onion",
            "quantity_qtl": 60
        }
        response = self.app.post('/api/mandi/recommend-best', 
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('best_mandi', data)
        self.assertIn('net_profit', data['best_mandi'])
        self.assertTrue(data['best_mandi']['net_profit'] > 0)

    def test_crop_recommendation(self):
        payload = {
            "season": "Kharif",
            "soil": "Black Soil",
            "water_availability": "Medium",
            "land_acres": 2.5
        }
        response = self.app.post('/api/crop/recommend',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['top_recommendations']) > 0)

    def test_price_trends(self):
        response = self.app.get('/api/mandi/trends?crop=Wheat')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['history']['prices']), 30)
        self.assertEqual(len(data['forecast']['prices']), 14)

    def test_chat_advisor(self):
        payload = {
            "message": "How do I protect crops from unseasonal rainfall?",
            "language": "en"
        }
        response = self.app.post('/api/advisor/chat',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('Drainage', data['reply'])

    def test_crop_advisor_full(self):
        payload = {
            "season": "Kharif",
            "soil": "Black Soil",
            "irrigation": "Borewell",
            "previous_crop": "Soyabean",
            "nitrogen": 130,
            "phosphorus": 40,
            "potassium": 160,
            "ph": 6.8,
            "land_acres": 3.0
        }
        response = self.app.post('/api/crop/advisor-full',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('soil_health_diagnostic', data)
        self.assertIn('advisory', data)
        self.assertTrue(len(data['advisory']['fertilizer_schedule']) > 0)
        self.assertTrue(data['advisory']['financial_summary']['est_net_profit_inr'] > 0)

    def test_climate_risk_assessment(self):
        payload = {
            "crop": "Wheat",
            "growth_stage": "Grain / Pod Filling",
            "district": "Ludhiana",
            "state": "Punjab"
        }
        response = self.app.post('/api/climate/risk-assessment',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('composite_risk', data)
        self.assertIn('threat_indices', data)
        self.assertIn('emergency_protocols', data)
        self.assertIn('pmfby_claim_guide', data)
        self.assertTrue(data['composite_risk']['score'] > 0)
        self.assertTrue(len(data['emergency_protocols']['pre_disaster_actions']) > 0)

    def test_aws_architecture(self):
        response = self.app.get('/api/aws/architecture')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['region'], 'ap-southeast-2')
        self.assertIn('Amazon Bedrock', data['stack_overview'])
        self.assertIn('DynamoDB', data['stack_overview'])
        self.assertIn('Lambda', data['stack_overview'])
        service_names = [s['service'] for s in data['services']]
        for name in (
            'Amazon S3', 'Amazon CloudFront', 'Amazon Route 53', 'Amazon API Gateway',
            'AWS Lambda', 'Amazon Bedrock', 'Amazon SageMaker', 'Amazon DynamoDB',
            'Amazon Cognito', 'Amazon CloudWatch', 'AWS X-Ray', 'AWS IAM',
            'AWS KMS', 'AWS Secrets Manager',
        ):
            self.assertIn(name, service_names)
        legacy = self.app.get('/api/gcp/architecture')
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(json.loads(legacy.data)['platform'], 'AgriMitra AI on AWS')

    def test_market_intelligence(self):
        payload = {
            "crop": "Soyabean",
            "farmer_district": "Nashik",
            "farmer_state": "Maharashtra",
            "quantity_qtl": 80
        }
        response = self.app.post('/api/market/intelligence',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('intelligence', data)
        self.assertIn('storage_economics', data)
        self.assertIn('top_arbitrage_destinations', data)
        self.assertIn('faq_quality_standards', data)
        intel = data['intelligence']
        self.assertIn('action_signal', intel)
        self.assertIn('action_badge', intel)
        self.assertIn('price_30d_expected', intel)
        self.assertTrue(intel['action_signal'] in ['HOLD / STORE', 'SELL IMMEDIATELY'])
        self.assertTrue(len(data['top_arbitrage_destinations']) > 0)
        self.assertTrue(data['storage_economics']['total_holding_cost_per_qtl'] > 0)

    def test_multilingual_chat_languages(self):
        languages = ['te', 'ta', 'kn', 'hi', 'en']
        for lang in languages:
            payload = {
                "message": "What fertilizer should I apply?",
                "language": lang
            }
            response = self.app.post('/api/advisor/chat',
                                     data=json.dumps(payload),
                                     content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['language'], lang)
            self.assertIn('Amazon Bedrock', data['powered_by'])
            self.assertTrue(len(data['reply']) > 20)

    def test_farmer_profile_and_history(self):
        payload = {
            "farmer_id": "farmer-test-1",
            "name": "Lakshmi",
            "state": "Maharashtra",
            "district": "Nashik",
            "language": "en"
        }
        saved = self.app.post('/api/farmer/profile',
                              data=json.dumps(payload),
                              content_type='application/json')
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(json.loads(saved.data)['storage'], 'memory')
        loaded = self.app.get('/api/farmer/profile?farmer_id=farmer-test-1')
        self.assertEqual(json.loads(loaded.data)['profile']['district'], 'Nashik')
        history = self.app.get('/api/farmer/history?farmer_id=farmer-test-1')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(json.loads(history.data)['status'], 'success')

if __name__ == '__main__':
    unittest.main()
