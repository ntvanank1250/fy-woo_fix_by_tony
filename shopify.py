import csv
import math
import requests
import shutil
from urllib.request import Request, urlopen
import urllib.parse
from io import BytesIO
from PIL import ImageFile
from PIL import Image, ImageOps
import io
import os
import base64
from cartmigration.libs.utils import *
from cartmigration.models.basecart import LeBasecart


class LeCartShopify(LeBasecart):
	FORMAT_DATETIME = 'y-m-d h:i:s'
	TABLE_SHOPIFY_REVIEW = 'shopify_review'
	TABLE_SHOPIFY_LANGIFY = 'shopify_langify'
	SP_MANU = 'manufacturers_table_construct'
	API_VERSION = '2020-01'
	TYPE_SMART_COLLECTION = 'smart'
	TYPE_CUSTOM_COLLECTION = 'custom'
	MAX_QTY = 1000000000


	def __init__(self):
		super().__init__()
		self._api_url = None
		self._location_id = None
		self._theme_data = dict()
		self._shopify_countries = dict()
		self.last_header = ''
		self._allow_clear_warning = True
		self._version_api = None


	def get_api_info(self):
		return {
			# "api_key": "API Key",
			'password': "API Password"
		}


	def display_setup_source(self, request):
		super().display_setup_source(request)
		api_shop = self.api('shop.json')
		if not api_shop:
			return response_api('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
		try:
			shop = json_decode(api_shop)
			if 'errors' in shop:
				return response_api('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
		except:
			return response_api('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
		return response_success()


	def display_setup_target(self, request):
		super().display_setup_target(request)
		api_shop = self.api('shop.json')
		if not api_shop:
			return response_api('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
		try:
			shop = json_decode(api_shop)
			if 'errors' in shop:
				return response_api('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
		except:
			return response_api('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
		return response_success()


	def display_config_source(self):
		parent = super().display_config_source()
		if parent['result'] != 'success':
			return parent
		api_shop = self.api('shop.json')
		if not api_shop:
			response = response_error('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
			response['elm'] = '#error-api'
			return response
		try:
			shop = json_decode(api_shop)
			if 'errors' in shop:
				response = response_error('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
				response['elm'] = '#error-api'
				return response
		except:
			response = response_error('Shopify API Password is not correct!', '#src-api-error', 'Info incorrect')
			response['elm'] = '#error-api'
			return response
		currency = shop.get('shop', dict()).get('currency', 'USD')
		self._notice['src']['language_default'] = 1
		self._notice['src']['category_root'] = 1
		self._notice['src']['currency_default'] = currency
		self._notice['src']['site'] = {
			'1': 'Default Shop'
		}
		self._notice['src']['category_data'] = {
			'1': 'Default Category'
		}
		self._notice['src']['languages'] = {
			'1': 'Default language'
		}

		self._notice['src']['order_status'] = {
			'pending': "Pending",
			'authorized': "Authorized",
			'partially_paid': "Partially Paid",
			'paid': "Paid",
			'partially_refunded': "Partially Refunded",
			'refunded': "Refunded",
			'voided': "Voided"
		}

		self._notice['src']['currencies'] = {
			currency: currency
		}
		self._notice['src']['support']['country_map'] = False
		self._notice['src']['support']['customer_group_map'] = False
		self._notice['src']['support']['manufacturers'] = True
		self._notice['src']['support']['reviews'] = True
		self._notice['src']['support']['add_new'] = True
		self._notice['src']['support']['clear_shop'] = True
		self._notice['src']['support']['pre_prd'] = False
		self._notice['src']['support']['pre_cus'] = False
		self._notice['src']['support']['smart_collection'] = False
		self._notice['src']['support']['pre_ord'] = True
		self._notice['src']['support']['seo_301'] = True
		self._notice['src']['support']['pages'] = True
		self._notice['src']['support']['blogs'] = True
		self._notice['src']['support']['coupons'] = True
		# self._notice['src']['support']['seo'] = True
		self._notice['src']['config']['seo_module'] = self.get_list_seo()
		return response_success()


	def display_config_target(self):
		parent = super().display_config_target()
		if parent['result'] != 'success':
			return parent
		api_shop = self.api('shop.json')
		if not api_shop:
			response = response_error('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
			response['elm'] = '#error-api'
			return response
		try:
			shop = json_decode(api_shop)
			if 'errors' in shop:
				response = response_error('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
				response['elm'] = '#error-api'
				return response
		except:
			response = response_error('Shopify API Password is not correct!', '#target-api-error', 'Info incorrect')
			response['elm'] = '#error-api'
			return response
		created_at = shop.get('shop', dict()).get('timezone')
		if to_str(created_at):
			self._notice['target']['config']['time_zone'] = to_str(created_at)[4:10]
			if self._notice['src']['cart_type'] == 'bigcommerce':
				self._notice['target']['config']['time_zone'] = '-00:00'
		currency = shop.get('shop', dict()).get('currency', 'USD')
		shopify_plan = shop.get('shop', dict()).get('plan_name', 'affiliate')
		# self._notice['target']['shopify_plan_name'] = shopify_plan
		self._notice['target']['language_default'] = 1
		self._notice['target']['category_root'] = 1
		self._notice['target']['currency_default'] = currency
		self._notice['target']['site'] = {
			'1': 'Default Shop'
		}
		self._notice['target']['category_data'] = {
			'1': 'Default Category'
		}
		self._notice['target']['languages'] = {
			'1': 'Default language'
		}

		self._notice['target']['order_status'] = {
			'pending': "Pending",
			'authorized': "Authorized",
			'partially_paid': "Partially Paid",
			'paid': "Paid",
			'partially_refunded': "Partially Refunded",
			'refunded': "Refunded",
			'voided': "Voided",
			# 'unpaid': "Unpaid"
		}
		self._notice['target']['currencies'] = {
			currency: currency
		}
		themes = self.api('themes.json')
		themes = json_decode(themes)
		if themes and themes.get('themes') and to_len(themes['themes']) < 20:
			self._notice['target']['support']['img_des'] = True
		self._notice['target']['support']['pages'] = True
		self._notice['target']['support']['country_map'] = False
		self._notice['target']['support']['customer_group_map'] = False
		if self.is_shopify():
			self._notice['target']['support']['order_status_map'] = False

		self._notice['target']['support']['manufacturers'] = False
		self._notice['target']['support']['taxes'] = False
		self._notice['target']['support']['reviews'] = True
		self._notice['target']['support']['add_new'] = True
		self._notice['target']['support']['clear_shop'] = True
		self._notice['target']['support']['pre_prd'] = False
		self._notice['target']['support']['pre_cus'] = False
		self._notice['target']['support']['pre_ord'] = True
		self._notice['target']['support']['smart_collection'] = True
		self._notice['target']['support']['languages_select'] = True
		self._notice['target']['support']['seo_301'] = True
		self._notice['target']['support']['seo'] = False
		self._notice['target']['support']['blogs'] = True
		self._notice['target']['support']['update_latest_data'] = True
		self._notice['target']['config']['entity_update']['products'] = True
		self._notice['target']['support']['coupons'] = True
		self._notice['target']['support']['multi_languages_select'] = True
		if self._notice['target'].get('disable_reload'):
			self._notice['target']['disable_reload']['languages'] = True
			self._notice['target']['disable_reload']['order_status'] = True
		shopify_reviews_table = self.reviews_table_construct()
		table_query = self.dict_to_create_table_sql(shopify_reviews_table)
		if table_query['result'] != 'success':
			return error_database()
		self.query_raw(table_query['query'])
		return response_success()


	def get_query_display_import_source(self, update = False):
		tax_imported = 0
		if self._notice['config']['add_new']:
			recent_data = self.get_recent(self._migration_id)
			if recent_data:
				for entity_type, data in recent_data['process'].items():
					# if self._notice['config'].get('update_latest_data') and self._notice['target']['config'].get('entity_update', dict()).get(entity_type):
					#     self._notice['process'][entity_type]['total_update'] = data['total']
					self._notice['process'][entity_type]['id_src'] = data['id_src']
					if entity_type == 'categories':
						self._notice['process'][entity_type]['id_src_smart'] = data.get('id_src_smart', 0)
						self._notice['process'][entity_type]['type'] = 'custom'
					if not update:
						self._notice['process'][entity_type]['total'] = 0
						self._notice['process'][entity_type]['imported'] = 0
						self._notice['process'][entity_type]['error'] = 0
					else:
						self._notice['process'][entity_type]['id_src'] = 0
					if entity_type == 'taxes':
						tax_imported = data['imported']
		if self._notice['config']['add_new'] and not update:
			custom_collections_api = self.api('custom_collections.json?since_id=' + to_str(self._notice['process']['categories']['id_src']))
			smart_collection_api = self.api('smart_collections.json?since_id=' + to_str(self._notice['process']['categories'].get('id_src_smart', 0)))
		else:
			custom_collections_api = self.api('custom_collections/count.json?since_id=' + to_str(self._notice['process']['categories']['id_src']))
			smart_collection_api = self.api('smart_collections/count.json?since_id=' + to_str(self._notice['process']['categories'].get('id_src_smart', 0)))
		products_api = self.api('products/count.json?since_id=' + to_str(self._notice['process']['products']['id_src']))
		customers_api = self.api('customers/count.json?since_id=' + to_str(self._notice['process']['customers']['id_src']))
		orders_api = self.api('orders/count.json?status=any&since_id=' + to_str(self._notice['process']['orders']['id_src']))
		pages_api = self.api('pages/count.json?status=any&since_id=' + to_str(self._notice['process']['pages']['id_src']))
		blogs_api = self.api('articles/count.json?since_id=' + to_str(self._notice['process']['blogs']['id_src']))

		# todo: get manufacturers
		if self._notice['config']['manufacturers']:
			queries = self.dict_to_create_table_sql(self.manufacturers_table_construct())
			self.query_raw(queries['query'])
			manufacturers_api = True
			page = 0
			all_queries = list()
			check_exist = list()
			manufacturer_link = 'fields=vendor&limit=250'
			next_link = ''
			while manufacturers_api:
				manufacturers_api = self.api('products.json?' + manufacturer_link + '&time=' + to_str(to_int(time.time())))
				if not manufacturers_api:
					return response_error(self.console_error("Could not get data from Shopify"))
				manufacturers = json_decode(manufacturers_api)
				if not manufacturers.get('products'):
					manufacturers_api = False
					continue
				for manufacture in manufacturers['products']:
					check_map_exist = self.select_obj(self.SP_MANU, {
						'name': manufacture['vendor'],
					})
					if manufacture['vendor'] in check_exist or (check_map_exist and check_map_exist['data']):
						continue
					manu_data = {
						'name': manufacture['vendor'],
					}
					check_exist.append(manufacture['vendor'])
					all_queries.append(manu_data)
				link = self.last_header.get('link')
				if link and 'next' in link:
					list_link = link.split(',')
					for link_row in list_link:
						if 'next' in link_row:
							next_link = link_row.split(';')[0]
				if not next_link:
					break
				manufacturer_link = to_str(next_link.split('products.json?')[1]).strip('<>')
				next_link = ''
			if all_queries:
				self.insert_multiple_obj(self.SP_MANU, all_queries)
		# end
		if self._notice['config']['add_new'] and not update:
			coupons_api = self.api('price_rules.json?since_id=' + to_str(self._notice['process']['coupons']['id_src']))
		else:
			coupons_api = self.api('price_rules/count.json?since_id=' + to_str(self._notice['process']['coupons']['id_src']))
		if (not custom_collections_api) and (not smart_collection_api) and (not products_api) and (not customers_api) and (
				not orders_api):
			return response_error('Could not get data from shopify')

		custom_collections = json_decode(custom_collections_api)
		smart_collection = json_decode(smart_collection_api)
		if self._notice['config']['add_new'] and not update:
			cat_cus_count_temp = to_len(custom_collections['custom_collections'])
			cat_smrt_count_temp = to_len(smart_collection['smart_collections'])

			cat_cus_count = cat_cus_count_temp
			cat_smrt_count = cat_smrt_count_temp

			while cat_cus_count_temp == 50:
				last_id = custom_collections['custom_collections'][-1]['id']
				custom_collections = self.api('custom_collections.json?since_id=' + to_str(last_id))
				custom_collections = json_decode(custom_collections)
				cat_cus_count_temp = to_len(custom_collections['custom_collections'])
				cat_cus_count += cat_cus_count_temp
			while cat_smrt_count_temp == 50:
				last_id = smart_collection['smart_collections'][-1]['id']
				smart_collection = self.api('smart_collections.json?since_id=' + to_str(last_id))
				smart_collection = json_decode(smart_collection)
				cat_smrt_count_temp = to_len(smart_collection['smart_collections'])
				cat_smrt_count += cat_smrt_count_temp
		else:
			cat_cus_count = custom_collections.get('count', 0)
			cat_smrt_count = smart_collection.get('count', 0)

		cat_count = cat_cus_count + cat_smrt_count
		products = json_decode(products_api)
		customers = json_decode(customers_api)
		orders = json_decode(orders_api)
		pages = json_decode(pages_api)
		blogs = json_decode(blogs_api)
		coupons = json_decode(coupons_api)
		pro_count = products.get('count', 0)
		cus_count = customers.get('count', 0)
		ord_count = orders.get('count', 0)
		page_count = pages.get('count', 0)
		blog_count = blogs.get('count', 0)
		if self._notice['config']['add_new'] and not update:
			coupon_count = to_len(coupons)
		else:
			coupon_count = coupons.get('count', 0)

		manufacture_count = 0
		if self._notice['config']['manufacturers']:
			where = 'id > ' + to_str(self._notice['process']['manufacturers']['id_src'])
			manufacture_count = self.count_table(self.SP_MANU, where)

		review_count = 0
		if self._notice['config']['reviews']:
			recent_review = ''
			if self._notice['config']['add_new']:
				recent_review = " id NOT IN (SELECT id_src FROM " + TABLE_MAP + " WHERE type = 'review' and migration_id = " + to_str(self._migration_id) + ") AND "
			review_query = "SELECT COUNT(1) AS count FROM " + self.get_table_name("src_" + self.TABLE_SHOPIFY_REVIEW) + " WHERE " + recent_review + "migration_id = " + to_str(self._migration_id)
			read = self.select_raw(review_query)
			if read['result'] == 'success' and read['data']:
				review_count = read['data'][0]['count']
		real_totals = {
			'taxes': 0 if tax_imported else 1,
			'manufacturers': manufacture_count,
			'categories': cat_count,
			'products': pro_count,
			'customers': cus_count,
			'orders': ord_count,
			'reviews': review_count,
			'pages': page_count,
			'blogs': blog_count,
			'coupons': coupon_count
		}
		# for key, total in real_totals.items():
		#     self._notice['process'][key]['total'] = total
		self._notice['process']['categories']['custom_count'] = cat_cus_count
		self._notice['process']['categories']['smart_count'] = cat_smrt_count
		return real_totals


	def display_import_source(self):
		count = self.get_query_display_import_source()
		for key, total in count.items():
			self._notice['process'][key]['total'] = total
		return response_success()


	def display_update_source(self):
		count_recent = self.get_query_display_import_source()
		for key, total in count_recent.items():
			self._notice['process'][key]['total'] = total
		count_all = self.get_query_display_import_source(True)
		count = {
			'taxes': 1,
			'manufacturers': to_int(count_all['manufacturers']) - to_int(count_recent['manufacturers']),
			'categories': to_int(count_all['categories']) - to_int(count_recent['categories']),
			'products': to_int(count_all['products']) - to_int(count_recent['products']),
			'customers': to_int(count_all['customers']) - to_int(count_recent['customers']),
			'orders': to_int(count_all['orders']) - to_int(count_recent['orders']),
			'reviews': to_int(count_all['reviews']) - to_int(count_recent['reviews']),
			'pages': to_int(count_all['pages']) - to_int(count_recent['pages']),
			'blogs': to_int(count_all['blogs']) - to_int(count_recent['blogs']),
			'coupons': to_int(count_all['coupons']) - to_int(count_recent['coupons'])
		}
		for key, total in count.items():
			self._notice['process'][key]['total_update'] = total
		if self._notice['config']['add_new']:
			recent_data = self.get_recent(self._migration_id)
			if recent_data:
				for entity_type, data in recent_data['process'].items():
					self._notice['process'][entity_type]['id_src'] = data['id_src']
					self._notice['process'][entity_type]['id_src_smart'] = data.get('id_src_smart', 0)
					# self._notice['process'][entity_type]['total'] = 0
					self._notice['process'][entity_type]['imported'] = 0
					self._notice['process'][entity_type]['error'] = 0
		return response_success()


	def display_confirm_source(self):
		parent = super().display_confirm_source()
		if parent['result'] != 'success':
			return parent
		access_scopes = self.get_access_scopes()
		fail_scope = list()
		if access_scopes:
			list_scope = {
				'products': 'read_products',
				'categories': 'read_products',
				'customers': 'read_customers',
				'orders': 'read_orders',
				'blogs': 'read_themes,read_content',
				'pages': 'read_themes,read_content',
				'coupons': 'read_price_rules'
			}
			for config, scopes in list_scope.items():
				scope = scopes.split(',')
				for row in scope:
					if self._notice['config'].get(config) and row not in access_scopes and row not in fail_scope:
						fail_scope.append(row)
		if fail_scope:
			self.log(','.join(fail_scope), self.get_type() + '_scope')
			return response_error('To support these selected entities, your entered Shopify API needs the following permission: ' + ','.join(fail_scope) + '. Details guide can be read {}. Please correct and retry.'.format(url_to_link('https://litextension.com/faq/docs/shopping-cart-questions/shopify/where-can-i-get-shopify-api-password', 'here')), '#form-entities', 'Shopify API Permission Missing')
		entities = ['reviews']
		folder_upload = self.get_folder_upload(self._migration_id)
		for entity in entities:
			self._notice['process'][entity]['total_view'] = 0
			if self._notice['config'][entity] and self._notice['src']['config']['file'].get(entity, dict()).get('upload'):
				file_upload = self.get_upload_file_name(entity)
				filename = folder_upload.rstrip('/') + '/' + file_upload.strip('/')
				encoding = ['utf-8', 'utf-16', 'cp1252', 'latin1', 'iso-8859-1']
				num_row = 0
				if os.path.isfile(filename):
					for encode in encoding:
						try:
							with open(filename, encoding = encode) as f:
								num_row = sum(1 for line in f) - 1
								break
						except:
							continue

					old_num_row = 0
					if self._notice['config']['recent']:
						if 'total_view' in self._notice['process'][entity]:
							old_num_row = self._notice['process'][entity]['total_view']

					self._notice['process'][entity]['total_view'] = num_row - old_num_row

		return response_success()


	def display_confirm_target(self):
		parent = super().display_confirm_target()
		if parent['result'] != 'success':
			return parent
		access_scopes = self.get_access_scopes()
		fail_scope = list()
		if access_scopes:
			list_scope = {
				'products': 'write_products,write_inventory,read_locations,read_themes,write_themes',
				'img_des': 'read_themes,write_themes',
				'blogs': 'read_themes,write_themes,read_content,write_content',
				'pages': 'read_themes,write_themes,read_content,write_content',
				'categories': 'write_products',
				'customers': 'write_customers',
				'orders': 'write_orders',
				'coupons': 'write_price_rules',
			}
			for config, scopes in list_scope.items():
				scope = scopes.split(',')
				for row in scope:
					if self._notice['config'].get(config) and row not in access_scopes and row not in fail_scope:
						fail_scope.append(row)
		if fail_scope:
			self.log(','.join(fail_scope), self.get_type() + '_scope')
			return response_error('To support these selected entities, your entered Shopify API needs the following permission: ' + ','.join(fail_scope) + '. Details guide can be read {}. Please correct and retry.'.format(url_to_link('https://litextension.com/faq/docs/shopping-cart-questions/shopify/where-can-i-get-shopify-api-password/', 'here')), '#form-entities', 'Shopify API Permission Missing')
		self._notice['target']['clear']['function'] = 'clear_target_taxes'
		self._notice['target']['clear_demo']['function'] = 'clear_target_products_demo'
		return response_success()


	def reviews_table_construct(self):
		return {
			'table': self.TABLE_SHOPIFY_REVIEW if self.get_type() == 'target' else "src_" + self.TABLE_SHOPIFY_REVIEW,
			'rows': {
				'migration_id': 'BIGINT',
				'id': 'BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY',
				'product_handle': 'TEXT',
				'state': 'TEXT',
				'rating': 'TEXT',
				'title': 'TEXT',
				'author': 'TEXT',
				'email': 'TEXT',
				'location': 'TEXT',
				'body': 'TEXT',
				'reply': 'TEXT',
				'created_at': 'TEXT',
				'replied_at': 'TEXT',
			},
			'validation': ['product_handle', 'state', 'rating', 'title', 'author', 'email', 'body', 'created_at'],
			'file': 'reviews'
		}


	# todo: clear
	def clear_target_taxes(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_manufacturers',
		}
		self._notice['target']['clear'] = next_clear
		return next_clear


	def clear_target_manufacturers(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_categories',
		}
		self._notice['target']['clear'] = next_clear
		return next_clear


	def clear_target_categories(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_products',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['categories']:
			return next_clear
		try:
			all_collections = self.api('custom_collections.json?limit=100')
			while all_collections:
				all_collections = json_decode(all_collections)
				if not all_collections.get('custom_collections'):
					break
				for collect in all_collections['custom_collections']:
					id_collect = collect['id']
					res = self.api('custom_collections/' + to_str(id_collect) + '.json', None, 'Delete')
				# a = res
				all_collections = self.api('custom_collections.json?limit=100')
				self.sleep_time(0.1)
			all_collections = self.api('smart_collections.json?limit=100')

			while all_collections:
				if not all_collections:
					return next_clear
				all_collections = json_decode(all_collections)
				if not all_collections.get('smart_collections'):
					return next_clear
				for collect in all_collections['smart_collections']:
					id_collect = collect['id']
					res = self.api('smart_collections/' + to_str(id_collect) + '.json', None, 'Delete')
				# a = res
				all_collections = self.api('smart_collections.json?limit=100')
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear
		return next_clear


	def clear_target_products(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_orders',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['products']:
			return next_clear
		try:
			themes = self.api('themes.json')
			themes = json_decode(themes)
			if themes and themes.get('themes'):
				for theme in themes['themes']:
					if 'Litextension image description' in theme['name']:
						res = self.api('themes/' + to_str(theme['id']) + '.json', None, 'DELETE')
			all_products = self.api('products.json?limit=100')
			while all_products:
				if not all_products:
					return next_clear
				all_products = json_decode(all_products)
				if not all_products.get('products'):
					return next_clear
				for product in all_products['products']:
					id_product = product['id']
					res = self.api('products/' + to_str(id_product) + '.json', None, 'Delete')
				all_products = self.api('products.json?limit=100')
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear

		return next_clear


	def clear_target_customers(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_pages',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['customers']:
			return next_clear
		list_customer_skip = list()
		try:
			all_customers = self.api('customers.json?since_id=0&limit=100')
			id_customer = 0
			while all_customers:
				if not all_customers:
					return next_clear
				all_customers = json_decode(all_customers)
				if not all_customers.get('customers'):
					return next_clear
				for customer in all_customers['customers']:
					id_customer = to_str(customer['id'])
					res = self.api('customers/' + to_str(id_customer) + '.json', None, 'Delete')
				# res = json_decode(res)
				# if res and res.get('errors'):
				# 	if isinstance(res['errors'], str):
				# 		if res['errors'] == 'Error deleting customer':
				# 			list_customer_skip.append(id_customer)
				# 	else:
				# 		if res['errors'].get('base', list()):
				# 			if res['errors']['base'][0] == 'Cannot delete orders brokered by Shopify':
				# 				list_customer_skip.append(id_customer)
				# if list_customer_skip and all_customers['customers'] and to_len(list_customer_skip) == to_len(all_customers['customers']):
				# 	break
				if to_len(all_customers['customers']) < 100:
					break
				all_customers = self.api('customers.json?limit=100&since_id={}'.format(id_customer))
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear
		return next_clear


	def clear_target_orders(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_customers',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['orders']:
			return next_clear
		list_order_skip = list()
		try:
			all_orders = self.api('orders.json?status=any&limit=100')
			while all_orders:
				if not all_orders:
					return next_clear
				all_orders = json_decode(all_orders)
				if not all_orders.get('orders'):
					return next_clear
				for order in all_orders['orders']:
					id_order = to_str(order['id'])
					if id_order in list_order_skip:
						continue
					res = self.api('orders/' + id_order + '.json', None, 'Delete')
					res = json_decode(res)
					if res and res.get('errors', dict()).get('base', list()):
						if res['errors']['base'][0] == 'Cannot delete orders brokered by Shopify':
							list_order_skip.append(id_order)
				if list_order_skip and all_orders['orders'] and len(list_order_skip) == len(all_orders['orders']):
					break
				all_orders = self.api('orders.json?status=any&limit=100')
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear
		return next_clear


	def clear_target_reviews(self):
		next_clear = {
			'result': 'success',
			'function': '',
			'msg': ''
		}
		if not self._notice['config']['reviews']:
			return next_clear
		delete = self.delete_obj(self.TABLE_SHOPIFY_REVIEW, {
			'migration_id': self._migration_id,
		})
		file_path = get_pub_path() + '/media/' + to_str(self._migration_id)
		if os.path.isdir(file_path):
			shutil.rmtree(file_path)
		if not delete:
			return error_database()
		return next_clear


	def clear_target_blogs(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_coupons',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['blogs']:
			return next_clear
		try:
			themes = self.api('themes.json')
			themes = json_decode(themes)
			if themes and themes.get('themes'):
				for theme in themes['themes']:
					if 'Litextension image blog description' in theme['name']:
						res = self.api('themes/' + to_str(theme['id']) + '.json', None, 'DELETE')
			all_blogs = self.api('blogs.json?limit=100')
			while all_blogs:
				if not all_blogs:
					return next_clear
				all_blogs = json_decode(all_blogs)
				if not all_blogs.get('blogs'):
					return next_clear
				for blog in all_blogs['blogs']:
					id_blog = blog['id']
					res = self.api('blogs/' + to_str(id_blog) + '.json', None, 'Delete')
				all_blogs = self.api('blogs.json?limit=100')
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear

		return next_clear


	def clear_target_coupons(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_reviews',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['coupons']:
			return next_clear
		try:

			all_price_rules = self.api('price_rules.json?limit=100')
			while all_price_rules:
				if not all_price_rules:
					return next_clear
				all_price_rules = json_decode(all_price_rules)
				if not all_price_rules.get('price_rules'):
					return next_clear
				for price_rule in all_price_rules['price_rules']:
					id_price = price_rule['id']
					res = self.api('price_rules/' + to_str(id_price) + '.json', None, 'Delete')
				all_price_rules = self.api('price_rules.json?limit=100')
				self.sleep_time(0.1)
		except Exception:
			self.log_traceback()
			return next_clear

		return next_clear


	def clear_target_pages(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_blogs',
			'msg': ''
		}
		self._notice['target']['clear'] = next_clear
		if not self._notice['config']['pages']:
			return next_clear
		try:
			themes = self.api('themes.json')
			themes = json_decode(themes)
			if themes and themes.get('themes'):
				for theme in themes['themes']:
					if 'Litextension image page description' in theme['name']:
						res = self.api('themes/' + to_str(theme['id']) + '.json', None, 'DELETE')
			all_pages = self.api('pages.json?limit=100')
			while all_pages:
				if not all_pages:
					return next_clear
				all_pages = json_decode(all_pages)
				if not all_pages.get('pages'):
					return next_clear
				for page in all_pages['pages']:
					id_page = page['id']
					res = self.api('pages/' + to_str(id_page) + '.json', None, 'Delete')
				all_pages = self.api('pages.json?limit=100')
				time.sleep(0.1)
		except Exception:
			self.log_traceback()
			return next_clear

		return next_clear


	# TODO: clear demo

	def clear_target_taxes_demo(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_manufacturers_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		return next_clear


	def clear_target_manufacturers_demo(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_categories_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		return self._notice['target']['clear_demo']


	def clear_target_categories_demo(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_products_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		if not self._notice['config']['categories']:
			return next_clear
		where = {
			'migration_id': self._migration_id,
			'type': self.TYPE_CATEGORY
		}
		categories = self.select_obj(TABLE_MAP, where)
		category_ids = list()
		if categories['result'] == 'success':
			category_ids = duplicate_field_value_from_list(categories['data'], 'id_desc')
		if not category_ids:
			return next_clear
		for category_id in category_ids:
			res = self.api('custom_collections/' + to_str(category_id) + '.json', None, 'Delete')
			if 'errors' in res:
				res = self.api('smart_collections/' + to_str(category_id) + '.json', None, 'Delete')

		self.delete_obj(TABLE_MAP, where)

		return next_clear


	def clear_target_products_demo(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_orders_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		if not self._notice['config']['products']:
			return next_clear
		where = {
			'migration_id': self._migration_id,
			'type': self.TYPE_PRODUCT
		}
		products = self.select_obj(TABLE_MAP, where)
		product_ids = list()
		if products['result'] == 'success':
			product_ids = duplicate_field_value_from_list(products['data'], 'id_desc')
		if not product_ids:
			return next_clear
		for product_id in product_ids:
			res = self.api('products/' + to_str(product_id) + '.json', None, 'Delete')
		self.delete_obj(TABLE_MAP, where)
		self.delete_obj(TABLE_MAP, {'migration_id': self._migration_id, 'type': self.TYPE_CHILD})
		return next_clear


	def clear_target_customers_demo(self):
		next_clear = {
			'result': 'process',
			'function': 'clear_target_reviews_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		if not self._notice['config']['customers']:
			return next_clear
		where = {
			'migration_id': self._migration_id,
			'type': self.TYPE_CUSTOMER
		}
		customers = self.select_obj(TABLE_MAP, where)
		customer_ids = list()
		if customers['result'] == 'success':
			customer_ids = duplicate_field_value_from_list(customers['data'], 'id_desc')
		if not customer_ids:
			return next_clear
		for customer_id in customer_ids:
			res = self.api('customers/' + to_str(customer_id) + '.json', None, 'Delete')
		return next_clear


	def clear_target_orders_demo(self):
		next_clear = {
			'result': 'success',
			'function': 'clear_target_customers_demo',
		}
		self._notice['target']['clear_demo'] = next_clear
		if not self._notice['config']['orders']:
			return next_clear
		where = {
			'migration_id': self._migration_id,
			'type': self.TYPE_ORDER
		}
		orders = self.select_obj(TABLE_MAP, where)
		order_ids = list()
		if orders['result'] == 'success':
			order_id_map = duplicate_field_value_from_list(orders['data'], 'id_desc')
			order_ids = list(set(order_ids + order_id_map))
		if not order_ids:
			return next_clear
		for order_id in order_ids:
			res = self.api('orders/' + to_str(order_id) + '.json', None, 'Delete')
		self.delete_obj(TABLE_MAP, where)
		return next_clear


	def clear_target_reviews_demo(self):
		next_clear = {
			'result': 'success',
			'function': '',
			'msg': ''
		}
		if not self._notice['config']['reviews']:
			return next_clear
		delete = self.delete_obj(self.TABLE_SHOPIFY_REVIEW, {
			'migration_id': self._migration_id,
		})
		file_path = get_pub_path() + '/media/' + to_str(self._migration_id)
		if os.path.isdir(file_path):
			shutil.rmtree(file_path)
		if not delete:
			return error_database()
		return next_clear


	def prepare_import_target(self):
		# api_shop = self.api('shop.json')
		# if not api_shop:
		# 	response = response_error('Shopify API Password is not correct(target)!')
		# 	response['elm'] = '#error-api'
		# 	return response
		# try:
		# 	shop = json_decode(api_shop)
		# 	if 'errors' in shop:
		# 		response = response_error('Shopify API Password is not correct(target)!')
		# 		response['elm'] = '#error-api'
		# 		return response
		# except:
		# 	response = response_error('Shopify API Password is not correct(target)!')
		# 	response['elm'] = '#error-api'
		# 	return response
		# shopify_plan = shop.get('shop', dict()).get('plan_name', 'affiliate')
		# self._notice['target']['shopify_plan_name'] = shopify_plan
		return response_success()


	# TODO: TAX
	def prepare_taxes_import(self):
		return self


	def prepare_taxes_export(self):
		return self


	def get_taxes_main_export(self):
		taxes = list()
		tax = {
			'id': '1',
			'code': 'Tax Rule Shopify'
		}
		taxes.append(tax)
		return response_success(taxes)


	def get_taxes_ext_export(self, taxes):
		tax_rates = self.api('countries.json')
		if not tax_rates:
			return response_error(self.console_error("Could not get tax rate data from Shopify"))
		tax_rates_data = json_decode(tax_rates)
		return response_success(tax_rates_data)


	def convert_tax_export(self, tax, taxes_ext):
		tax_product = list()
		tax_customer = list()
		tax_zone = list()
		tax_product_data = self.construct_tax_product()
		tax_product_data['id'] = 1
		tax_product_data['code'] = None
		tax_product_data['name'] = 'Product Tax Class Shopify'
		tax_product.append(tax_product_data)
		for country in taxes_ext['data']['countries']:
			if 'provinces' in country and country['provinces']:
				for province in country['provinces']:
					tax_zone_state = self.construct_tax_zone_state()
					tax_zone_state['id'] = province['id']
					tax_zone_state['name'] = province['name']
					tax_zone_state['state_code'] = province['code']

					tax_zone_country = self.construct_tax_zone_country()
					tax_zone_country['id'] = country['id']
					tax_zone_country['name'] = country['name']
					tax_zone_country['country_code'] = country['code']

					tax_zone_rate = self.construct_tax_zone_rate()
					tax_zone_rate['id'] = None
					tax_zone_rate['name'] = province['tax_name']
					tax_zone_rate['rate'] = province['tax']

					tax_zone_data = self.construct_tax_zone()
					tax_zone_data['id'] = None
					tax_zone_data['name'] = country['tax_name'] + ' - ' + province['tax_name'] if province[
						'tax_name'] else country['tax_name'] + ' - ' + province['code']
					tax_zone_data['country'] = tax_zone_country
					tax_zone_data['state'] = tax_zone_state
					tax_zone_data['rate'] = tax_zone_rate

					tax_zone.append(tax_zone_data)

			else:
				tax_zone_state = self.construct_tax_zone_state()

				tax_zone_country = self.construct_tax_zone_country()
				tax_zone_country['id'] = country['id']
				tax_zone_country['name'] = country['name']
				tax_zone_country['country_code'] = country['code']

				tax_zone_rate = self.construct_tax_zone_rate()
				tax_zone_rate['id'] = None
				tax_zone_rate['name'] = country['tax_name']
				tax_zone_rate['rate'] = country['tax']

				tax_zone_data = self.construct_tax_zone()
				tax_zone_data['id'] = None
				tax_zone_data['name'] = country['tax_name'] if country['tax_name'] else country['code']
				tax_zone_data['country'] = tax_zone_country
				tax_zone_data['state'] = tax_zone_state
				tax_zone_data['rate'] = tax_zone_rate

				tax_zone.append(tax_zone_data)

		tax_data = self.construct_tax()
		tax_data['id'] = tax['id']
		tax_data['name'] = tax['code']
		tax_data['tax_products'] = tax_product
		tax_data['tax_zones'] = tax_zone
		return response_success(tax_data)


	def get_tax_id_import(self, convert, tax, taxes_ext):
		return tax['id']


	def check_tax_import(self, convert, tax, taxes_ext):
		return self.get_map_field_by_src(self.TYPE_TAX, convert['id'], convert['code'])


	def router_tax_import(self, convert, tax, taxes_ext):
		return response_success('tax_import')


	def before_tax_import(self, convert, tax, taxes_ext):
		return response_success()


	def tax_import(self, convert, tax, taxes_ext):
		all_countries = self.api('countries.json')
		if not all_countries:
			return response_error(self.console_error("Could not get countries data from Shopify"))
		all_countries = json_decode(all_countries)

		if not convert['tax_zones']:
			return response_warning(self.console_error(
				"Tax id " + to_str(convert['id']) + " import failed. Error: Tax zones are not existed!"))
		tax_zones = convert['tax_zones']
		for tax_zone in tax_zones:
			country_code = tax_zone['country']['country_code']
			state_code = tax_zone['state']['state_code']
			rate = to_decimal(tax_zone['rate']['rate']) / 100
			check_country = False
			id_country = 0
			for country in all_countries['countries']:
				if country['code'] == country_code:
					check_country = True
					id_country = country['id']

			if not check_country:
				post_data = {
					'country': {
						'code': country_code,
					}
				}

				response = self.api('countries.json', post_data, 'Post')
				response = json_decode(response)
				check_response = self.check_response_import(response, {'id': country_code, 'code': country_code},
				                                            'country')
				if check_response['result'] != 'success':
					return check_response

				id_country = response['country']['id']

			if not state_code and id_country:
				put_data = {
					'country': {
						'id': id_country,
						'tax': rate
					}
				}
				response = self.api('countries/' + id_country + '.json', put_data, 'Put')
				response = json_decode(response)
				check_response = self.check_response_update(response, country_code, 'country')
				if check_response['result'] != 'success':
					return check_response
				continue

			country_detail = self.api('countries/' + id_country + '.json')
			if not country_detail:
				return response_warning('Could not get data country: ' + country_code)

			country_detail = json_decode(country_detail)
			check_state = False
			id_state = 0
			for province in country_detail['country']['provinces']:
				if province['code'] == state_code:
					check_state = True
					id_state = province['id']
			if check_state:
				put_data = {
					'province': {
						'id': id_state,
						'tax': rate
					}
				}
				response = self.api('countries/' + id_country + '/provinces/' + id_state + '.json', put_data,
				                    'Put')
				response = json_decode(response)
				check_response = self.check_response_update(response, country_code + ':' + state_code, 'province')
				if check_response['result'] != 'success':
					return check_response
		return response_success(0)


	def after_tax_import(self, tax_id, convert, tax, taxes_ext):
		return response_success()


	def addition_tax_import(self, convert, tax, taxes_ext):
		return response_success()


	# TODO: MANUFACTURER
	def prepare_manufacturers_import(self):
		return self


	def prepare_manufacturers_export(self):
		return self


	def get_manufacturers_main_export(self):
		id_src = self._notice['process']['manufacturers']['id_src']
		limit = self._notice['setting']['manufacturers']
		query = "SELECT * FROM " + self.SP_MANU + " WHERE id > " + to_str(id_src) + " ORDER BY id ASC LIMIT " + to_str(limit)
		manufacturers = self.select_raw(query)
		if manufacturers['result'] != 'success':
			return error_database()
		return manufacturers


	def get_manufacturers_ext_export(self, manufacturers):
		return response_success()


	def convert_manufacturer_export(self, manufacturer, manufacturers_ext):
		manufacturer_data = self.construct_manufacturer()
		manufacturer_data['id'] = manufacturer['id']
		manufacturer_data['name'] = manufacturer['name']
		return response_success(manufacturer_data)


	def get_manufacturer_id_import(self, convert, manufacturer, manufacturers_ext):
		return manufacturer['id']


	def check_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
		return False


	def router_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
		return response_success('manufacturer_import')


	def before_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
		return response_success()


	def manufacturer_import(self, convert, manufacturer, manufacturers_ext):
		return response_success(0)


	def after_manufacturer_import(self, manufacturer_id, convert, manufacturer, manufacturers_ext):
		return response_success()


	def addition_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
		return response_success()


	# TODO: CATEGORY
	def prepare_categories_import(self):
		return self


	def prepare_categories_export(self):
		self._notice['process']['categories']['type'] = 'custom'
		return self


	def get_categories_main_export(self):
		collection_type = self._notice['process']['categories'].get('type', 'custom')
		limit = self._notice['setting']['categories']
		categories_data = list()
		if collection_type == 'custom':
			id_src = self._notice['process']['categories']['id_src']
			collections = self.api('custom_collections.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit))
			if not collections:
				return response_error(self.console_error("Could not get category data from Shopify"))
			categories_page = json_decode(collections)
			# if 'custom_collections' in categories_page and not categories_page['custom_collections']:
			# 	return create_response('pass')
			categories_data = categories_page.get('custom_collections')
			if not categories_data:
				collection_type = 'smart'
		if collection_type == 'smart':
			id_src = self._notice['process']['categories'].get('id_src_smart')
			if not id_src:
				id_src = 0
			collections = self.api('smart_collections.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit))
			if not collections:
				return response_error(self.console_error("Could not get category data from Shopify"))
			categories_page = json_decode(collections)
			if 'smart_collections' in categories_page and not categories_page['smart_collections']:
				return create_response('pass')
			categories_data = categories_page['smart_collections']
		response = response_success(categories_data)
		response['type'] = collection_type
		return response


	def get_categories_ext_export(self, categories):
		extend = dict()
		for category in categories['data']:
			extend[category['id']] = dict()
			meta = False
			if 'rules' in category:
				meta = self.api('smart_collections/' + to_str(category['id']) + '/metafields.json')
			else:
				meta = self.api('custom_collections/' + to_str(category['id']) + '/metafields.json')
			if meta:
				category_meta = json_decode(meta)
				extend[category['id']]['meta'] = category_meta.get('metafields')
		return response_success(extend)


	def convert_category_export(self, category, categories_ext):
		category_data = self.construct_category()
		parent = self.construct_category_parent()
		parent['id'] = 0
		category_data['parent'] = parent
		category_data['id'] = category['id']
		category_data['active'] = True if category['published_at'] else False

		if 'image' in category:
			if 'src' in category['image']:
				real_path = re.sub("/\?.+/", "", to_str(category['image']['src']))
				real_path = real_path[:real_path.find('?')]
				category_data['thumb_image']['url'] = real_path
				category_data['thumb_image']['path'] = ''

		category_data['name'] = category['title']
		category_data['description'] = category['body_html']
		category_data['created_at'] = convert_format_time(category['published_at'], self.FORMAT_DATETIME)
		category_data['updated_at'] = convert_format_time(category['updated_at'], self.FORMAT_DATETIME)
		category_data['category'] = category
		category_data['categories_ext'] = categories_ext

		if 'meta' in categories_ext['data'][category['id']] and categories_ext['data'][category['id']]['meta']:
			for metafields in categories_ext['data'][category['id']]['meta']:
				if metafields['key'] == 'description_tag':
					category_data['meta_description'] = metafields['value']
				elif metafields['key'] == 'title_tag':
					category_data['meta_title'] = metafields['value']

		detect_seo = self.detect_seo()
		category_data['seo'] = getattr(self, 'categories_' + detect_seo)(category, categories_ext)

		return response_success(category_data)


	def finish_category_export(self):
		return response_success()


	def get_category_id_import(self, convert, category, categories_ext):
		return category['id']


	def check_category_import(self, convert, category, categories_ext):
		return self.get_map_field_by_src(self.TYPE_CATEGORY, convert['id'], convert['code'])


	def router_category_import(self, convert, category, categories_ext):
		return response_success('category_import')


	def before_category_import(self, convert, category, categories_ext):
		return response_success()


	def category_import(self, convert, category, categories_ext):
		id_desc = None
		handle = False
		category_name = self.strip_html_tag(convert['name'])
		new_cate_name = urllib.parse.quote(category_name)
		if not category_name:
			self.log_primary('categories', 'category name is empty', convert['id'])
			return create_response('skip_error')
		if 'disjunctive' in category or self._notice['config'].get('smart_collection'):
			smart_exist = self.api('smart_collections.json?title=' + new_cate_name + "&limit=4")
			smart_exist = json_decode(smart_exist)
			check_exist = False
			if smart_exist and isinstance(smart_exist, dict) and smart_exist.get('smart_collections') and to_len(smart_exist.get('smart_collections')) >= 1:
				category_name += ' ' + convert['parent'].get('name') if convert['parent'].get('name') else to_str(convert['id']) if convert['id'] else to_str(to_int(time.time()))
			post_data = {
				'smart_collection': {
					'title': category_name,
					'published': convert['active'],
					'disjunctive': category['disjunctive'] if 'disjunctive' in category else True,
					'body_html': get_value_by_key_in_dict(convert, 'description', ''),
					'updated_at': convert['updated_at']
				}
			}
			if convert['thumb_image']['url']:
				image_process = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
				if to_str(self._notice['src']['cart_type']) == 'bigcommerce':
					images = {
						'src': self.URL_PROXY + to_str(image_process['url'])
					}
				elif to_str(self._notice['src']['cart_type']) == 'bigcommerce':
					image_process['url'] = self.URL_PROXY + to_str(image_process['url'])
				image_data = self.resize_image(image_process['url'])
				if image_data:
					image_data['alt'] = to_str(convert['thumb_image']['label'])[:512]
					post_data['smart_collection']['image'] = image_data
				else:
					post_data['smart_collection']['image'] = {'src': image_process['url'], 'alt': to_str(convert['thumb_image']['label'])[:512]}

			# elif self._notice['src']['config'].get('auth'):
			# 	image_process['url'] = self.join_url_auth(image_process['url'])
			# 	name = os.path.basename(image_process['url'])
			# 	image_attachment = base64.b64encode(image_process['url'])
			# 	images = {
			# 		'attachment': image_attachment,
			# 		'alt': name,
			# 	}
			# else:
			# 	images = {
			# 		'src': image_process['url']
			# 	}
			# post_data['smart_collection']['image'] = images

			if convert['meta_description'] or convert['meta_title']:
				metafields = list()
				if convert['meta_description']:
					metafields.append({
						'key': 'description_tag',
						'value': get_value_by_key_in_dict(convert, 'meta_description', ''),
						'type': 'multi_line_text_field',
						'namespace': 'global'
					})

				if convert['meta_title']:
					metafields.append({
						'key': 'title_tag',
						'value': convert['meta_title'],
						'type': 'multi_line_text_field',
						'namespace': 'global'
					})
				if metafields:
					post_data['smart_collection']['metafields'] = metafields

			# shopify2shopify
			if category.get('rules'):
				post_data['smart_collection']['rules'] = list()
				for rule in category['rules']:
					post_data['smart_collection']['rules'].append({
						'column': rule['column'],
						'relation': rule['relation'],
						'condition': rule['condition']
					})
			else:
				rule = {
					'column': 'tag',
					'relation': 'equals',
					'condition': category_name.replace(',', '')
				}
				post_data['smart_collection']['rules'] = list()
				post_data['smart_collection']['rules'].append(rule)
			response = self.api('smart_collections.json', post_data, 'Post')
			response = json_decode(response)
			check_response = self.check_response_import(response, convert, 'category')
			if check_response['result'] != 'success':
				if 'image' in post_data['smart_collection']:
					del post_data['smart_collection']['image']
					response = self.api('smart_collections.json', post_data, 'Post')
					response = json_decode(response)
					check_response = self.check_response_import(response, convert, 'category')
					if check_response['result'] != 'success':
						self.log_primary('categories', check_response['msg'], convert['id'], convert['code'])
						return check_response
				else:
					self.log_primary('categories', check_response['msg'], convert['id'], convert['code'])
					return check_response
			# if check_exist:
			# category_name = category_name + ' ' + to_str(response['smart_collection']['id'])
			# update_data = {
			#   "smart_collection": {
			#     "title": category_name,
			#   }
			# }
			# self.api('smart_collections/' + to_str(response['smart_collection']['id']) + '.json', update_data, "PUT")

			id_desc = response['smart_collection']['id']
			handle = response['smart_collection']['handle']
			self.change_image_decription_category(post_data, 'smart_collection', id_desc, convert)

		else:
			post_data = {
				'custom_collection': {
					'title': category_name,
					'published': convert['active'],
					'body_html': get_value_by_key_in_dict(convert, 'description', ''),
					'updated_at': convert['updated_at']

				}
			}
			if convert['meta_description'] or convert['meta_title']:
				metafields = list()
				if convert['meta_description']:
					metafields.append({
						'key': 'description_tag',
						'value': get_value_by_key_in_dict(convert, 'meta_description', ''),
						'type': 'multi_line_text_field',
						'namespace': 'global'
					})

				if convert['meta_title']:
					metafields.append({
						'key': 'title_tag',
						'value': convert['meta_title'],
						'type': 'multi_line_text_field',
						'namespace': 'global'
					})
				if metafields:
					post_data['custom_collection']['metafields'] = metafields

			if convert['thumb_image']['url']:
				image_process = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
				if to_str(self._notice['src']['cart_type']) == 'bigcommerce':
					images = {
						'src': self.URL_PROXY + to_str(image_process['url'])
					}
				elif to_str(self._notice['src']['cart_type']) == 'bigcommerce':
					image_process['url'] = self.URL_PROXY + to_str(image_process['url'])
				image_data = self.resize_image(image_process['url'])
				if image_data:
					image_data['alt'] = to_str(convert['thumb_image']['label'])[:512]
					post_data['custom_collection']['image'] = image_data
				else:
					post_data['custom_collection']['image'] = {'src': image_process['url'], 'alt': to_str(convert['thumb_image']['label'])[:512]}

			response = self.api('custom_collections.json', post_data, 'Post')
			response = json_decode(response)
			check_response = self.check_response_import(response, convert, 'category')
			if check_response['result'] != 'success':
				if 'image' in post_data['custom_collection']:
					del post_data['custom_collection']['image']
					response = self.api('custom_collections.json', post_data, 'Post')
					response = json_decode(response)
					check_response = self.check_response_import(response, convert, 'category')
					if check_response['result'] != 'success':
						return check_response
				else:
					return check_response
			id_desc = response['custom_collection']['id']
			handle = response['custom_collection']['handle']
			self.change_image_decription_category(post_data, 'custom_collection', id_desc, convert)
		# seo
		if handle:
			if 'seo' in convert and convert['seo']:
				for seo_url in convert['seo']:
					seo_data = {
						'redirect': {
							'path': seo_url['request_path'],
							'target': '/collections/' + handle
						}
					}
					response_seo = self.api('redirects.json', seo_data, 'Post')
		# if self._notice["config"]['seo_plugin'] and self._notice["config"]["seo"]:
		# 	seo_name = self._notice["config"]["seo_plugin"]
		# model_seo = Bootstrap::getModel(seo_name)
		# data_seo = model_seo->getCategoriesSeoExport(this, category, categoriesExt)
		# for seo in data_seo:
		#	post_seo_data = array(
		#		'redirect': array(
		#			'path': seo['request_path'],
		#		                'target': '/collections/'. handle
		#		)
		#	)
		#	response_seo = self.api('redirects.json', post_seo_data, 'Post')

		self.insert_map(self.TYPE_CATEGORY, convert['id'], id_desc, convert['code'], category_name.replace(',', ''))
		return response_success(id_desc)


	def after_category_import(self, category_id, convert, category, categories_ext):
		# self.langify_import(category_id, self.TYPE_CATEGORY, convert)
		return response_success()


	def addition_category_import(self, convert, category, categories_ext):
		return response_success()


	# TODO: PRODUCT
	def prepare_products_import(self):
		return self


	def prepare_products_export(self):
		return self


	def get_products_main_export(self):
		imported = self._notice['process']['products']['imported']
		limit_data = self._notice['setting']['products']
		id_src = self._notice['process']['products']['id_src']
		page_data = math.floor(int(imported) / to_int(limit_data)) + 1
		products = self.api('products.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit_data))
		if not products:
			return response_error(self.console_error("Could not get data from Shopify"))
		products_page = json_decode(products)
		if not products_page:
			self.log("Can't get product data, id_src = " + to_str(id_src), 'get_main')
			return response_error()
		product_data = products_page.get('products')
		if product_data:
			return response_success(product_data)
		# check data empty
		count_product = self.api('products/count.json')
		count_product = json_decode(count_product)
		if count_product and count_product.get('count') and to_int(count_product['count']) <= to_int(self._notice['process']['products']['imported']):
			self.log('Migrate successfully product', 'product_full')
			return create_response('pass')
		self.log("Can't get product data, id_src = " + to_str(id_src), 'get_main')
		return response_error()


	def get_products_ext_export(self, products):
		extend = dict()
		for product in products['data']:
			meta = self.api("products/" + to_str(product['id']) + "/metafields.json")
			cat_cus = self.api('custom_collections.json?product_id=' + to_str(product['id']))
			cat_smart = self.api('smart_collections.json?product_id=' + to_str(product['id']))
			# Felix add inventory_items get code 18/2/2022
			variants = product['variants']
			inventory_items = dict()
			for variant in variants:
				inventory_item = self.api(f'inventory_items/{variant["inventory_item_id"]}.json')
				inventory_items.update({variant['id']: json_decode(inventory_item)['inventory_item']})
			if (not meta) or (not cat_cus) or (not cat_smart):
				return response_error(self.console_error("Could not get data from Shopify"))
			meta_to_array = json_decode(meta)
			cat_to_array_cus = json_decode(cat_cus)
			cat_to_array_smart = json_decode(cat_smart)
			extend[product['id']] = dict()
			extend[product['id']]['meta'] = meta_to_array['metafields']
			extend[product['id']]['custom_category'] = cat_to_array_cus['custom_collections']
			extend[product['id']]['smart_category'] = cat_to_array_smart['smart_collections']
			extend[product['id']]['inventory_items'] = inventory_items
		return response_success(extend)


	def convert_product_export(self, product, products_ext):
		product_data = self.construct_product()
		product_data['id'] = product['id']
		product_data['tags'] = product['tags']
		count_children = len(product['variants']) if product['variants'] else None
		if not count_children:
			return response_warning(self.warning_import_entity('Product', product['id'], None, "Product don't have variant."))
		if self.is_shopify():
			product_data['product_type'] = product['product_type']
		product_data['sku'] = product['variants'][0]['sku'] if product['variants'][0]['sku'] else product['variants'][0]['barcode']
		if product['variants'][0]['compare_at_price']:
			if to_decimal(product['variants'][0]['compare_at_price']) > to_decimal(product['variants'][0]['price']):
				product_data['special_price']['price'] = product['variants'][0]['price']
				product_data['special_price']['start_date'] = ''
				product_data['special_price']['end_date'] = ''
				product_data['price'] = product['variants'][0]['compare_at_price']
			else:
				product_data['price'] = product['variants'][0]['price']
		else:
			product_data['price'] = product['variants'][0]['price']
		product_data['tax']['id'] = 1
		product_data['weight'] = product['variants'][0]['weight']  # product['variants'][0]['grams'] if product['variants'][0]['weight_unit'] == 'g' else
		product_data['status'] = True if product['published_at'] else False
		qty = 0
		for variant in product['variants']:
			qty += to_int(variant['inventory_quantity'])
		product_data['qty'] = qty
		# product_data['manage_stock'] = True if product['variants'][0]['inventory_management'] and len(product['variants']) <= 1 else False
		product_data['manage_stock'] = True if product['variants'][0]['inventory_management'] else False
		if self.is_shopify():
			product_data['inventory_policy'] = product['variants'][0]['inventory_policy']
		product_data['is_in_stock'] = True if to_int(product['variants'][0]['inventory_quantity']) > 0 else False
		product_data['created_at'] = convert_format_time(''.join(product['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		product_data['updated_at'] = convert_format_time(''.join(product['updated_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		product_data['name'] = product['title']
		product_data['description'] = product['body_html']
		product_data['barcode'] = product['variants'][0]['barcode']
		# if product.get('image', {}).get('src', False):
		if get_value_by_key_in_dict(get_value_by_key_in_dict(product, 'image', dict()), 'src', False):
			real_path = re.sub("\?.+", "", to_str(product['image']['src']))
			product_data['thumb_image']['url'] = real_path
			product_data['thumb_image']['path'] = ''
			product_data['thumb_image']['label'] = product['image'].get('alt')
		# if

		if 'images' in product:
			# for
			for image in product['images']:
				if image['id'] == product['image']['id']:
					continue
				real_path = re.sub("\?.+", "", to_str(image['src']))
				product_image_data = self.construct_product_image()
				product_image_data['url'] = real_path
				product_image_data['label'] = image.get('alt')
				product_data['images'].append(product_image_data)
		# endfor
		# endif

		product_data['manufacturer']['name'] = product['vendor']
		if product['vendor'] and self._notice['config']['manufacturers']:
			check_exist = self.select_row(self.SP_MANU, {
				'name': product['vendor'],
			})
			if check_exist:
				product_data['manufacturer']['id'] = check_exist['id']
		# product_data['manufacturer']['code'] = product['vendor']
		# if

		if products_ext['data'][product['id']]['custom_category']:
			pro_to_cat = products_ext['data'][product['id']]['custom_category']
			# for

			for collection in pro_to_cat:
				product_category_data = self.construct_product_category()
				product_category_data['id'] = collection['id']
				product_data['categories'].append(product_category_data)
		# endfor
		# endif

		# if
		if products_ext['data'][product['id']]['smart_category']:
			pro_to_cat_smart = products_ext['data'][product['id']]['smart_category']
			for collection in pro_to_cat_smart:
				product_category_data = self.construct_product_category()
				product_category_data['id'] = collection['id']
				product_category_data['type'] = 'smart_category'
				product_data['categories'].append(product_category_data)
		# endif

		# if
		if products_ext['data'][product['id']]['meta']:
			product_attrs = list()
			for metafields in products_ext['data'][product['id']]['meta']:
				if metafields['key'] == 'description_tag':
					product_data['meta_description'] = metafields['value']
				elif metafields['key'] == 'title_tag':
					product_data['meta_title'] = metafields['value']
				else:
					# custom attr
					attribute = self.construct_product_attribute()
					attribute['option_name'] = metafields.get('key', '')
					attribute['option_code'] = metafields.get('key', '')
					attribute['option_value_name'] = metafields.get('value', '')
					attribute['option_type'] = metafields.get('value_type', '')
					attribute['namespace'] = metafields.get('namespace', '')
					product_attrs.append(attribute)

			if len(product_attrs) > 0:
				product_data['attributes'] = product_attrs
		else:
			product_data['meta_title'] = product['title']
		# endif
		detect_seo = self.detect_seo()
		product_data['seo'] = getattr(self, 'products_' + detect_seo)(product, products_ext)

		inventory_items = products_ext['data'][product['id']]['inventory_items']

		# get cost product
		if inventory_items.get(product['variants'][0]['id']):
			_cost = inventory_items[product['variants'][0]['id']]['cost']
			if _cost:
				product_data['cost'] = _cost

		# if
		# if product_data['type'] == 'configurable':
		children = list()
		# for
		variants_len = len(product['variants'])
		if to_int(variants_len) > 0:
			# product_data['type'] = self.PRODUCT_CONFIG
			for variant in product['variants']:
				if variant['title'] not in ['Default Title', 'Default']:
					child = self.construct_product_child()
					child['id'] = variant['id']
					child['type'] = 'simple'
					child['name'] = product['title'] + '-' + variant['title']
					child['sku'] = variant['sku']
					# image = ''
					# if product['image']['id'] == variant['image_id']:
					# 	image = product['image']['src']
					image = get_row_from_list_by_field(product['images'], 'id', variant['image_id'])
					if image:
						image = image.get('src')
					child['status'] = True if product['published_at'] else False
					if variant['compare_at_price']:
						if to_decimal(variant['compare_at_price']) > to_decimal(variant['price']):
							child['special_price']['price'] = variant['price']
							child['special_price']['start_date'] = ''
							child['special_price']['end_date'] = ''
							child['price'] = variant['compare_at_price']
						else:
							child['price'] = variant['price']
					else:
						child['price'] = variant['price']

					# get cost for child
					if inventory_items.get(variant['id']):
						_cost = inventory_items[variant['id']]['cost']
						if _cost:
							child['cost'] = _cost

					# child['thumb_image']['url'] = re.sub("\?.+", "", image)
					if image:
						# image_path = image.split('?')
						# child['thumb_image']['url'] = image_path[0]
						child['thumb_image']['url'] = re.sub("\?.+", "", to_str(image))
					child['thumb_image']['path'] = ''
					child['qty'] = variant['inventory_quantity']
					child['manage_stock'] = True if variant['inventory_management'] else False
					child['is_in_stock'] = True if to_int(variant['inventory_quantity']) > 0 else False
					child['weight'] = variant['weight']
					child['created_at'] = convert_format_time(''.join(variant['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
					child['updated_at'] = convert_format_time(''.join(variant['updated_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
					child_options = list()
					for i in range(1, 4):
						if variant['option' + to_str(i)]:
							child_option = self.construct_product_child_attribute()
							child_option['option_id'] = i
							child_option['option_type'] = 'select'
							child_option['option_name'] = get_row_value_from_list_by_field(product['options'], 'position', to_str(i), 'name')
							child_option['option_code_save'] = child_option['option_name']
							child_option['option_value_name'] = variant['option' + to_str(i)]
							child_option['option_value_code'] = child_option['option_value_name']
							child_option['option_value_code_save'] = child_option['option_value_name']
							child_options.append(child_option)
					if not child_options:
						continue
					child['attributes'] = child_options
					children.append(child)
					product_data['sku'] = self.convert_attribute_code(product_data['name'])
				else:
					product_data['sku'] = variant['sku'] if variant['sku'] else variant['barcode']

			# endfor
			product_data['children'] = children
		# endif
		product_data['type'] = self.PRODUCT_CONFIG if product_data['children'] else self.PRODUCT_SIMPLE
		return response_success(product_data)


	def get_product_id_import(self, convert, product, products_ext):
		return product['id']


	def check_product_import(self, convert, product, products_ext):
		if 'product' not in self._notice:
			self._notice['product'] = True
			self.clear_target_products()
			self.delete_obj('migration_map', where={'migration_id': self._migration_id, 'type': 'product'})
			self.delete_obj('migration_map', where={'migration_id': self._migration_id, 'type': 'product_child'})
			self.delete_obj('migration_map', where={'migration_id': self._migration_id, 'type': 'attr'})
			self.delete_obj('migration_map', where={'migration_id': self._migration_id, 'type': 'attr_option'})
			self.delete_obj('migration_map', where={'migration_id': self._migration_id, 'type': 'attr_value'})
		return self.get_map_field_by_src(self.TYPE_PRODUCT, convert['id'], convert['code'])
		

	def update_latest_data_product(self, product_id, convert, product, products_ext):
		product_import = self.get_map_field_by_src(self.TYPE_PRODUCT, convert['id'], convert['code'])
		if not product_import:
			return response_warning('The product has not been imported ' + to_str(convert['id']))

		# todo: update cate
		if not self._notice['config'].get('smart_collection'):
			product_collects = self.api('collects.json?product_id=' + to_str(product_import))
			if not product_collects:
				return response_error(self.console_error("Could not get data from Shopify"))
			collects = json_decode(product_collects)
			if not collects:
				self.log("Can't get collects data, id_src = " + to_str(product_import), 'get_main')
				return response_error()
			collects_data = collects.get('collects')
			if collects_data:
				for collect in collects_data:
					self.api('collects/' + to_str(collect['id']) + '.json', None, 'DELETE')

		if self._notice['config'].get('smart_collection'):
			tags = to_str(convert['tags']).split(',')
			for category in convert['categories']:
				category_name = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'], 'code_desc')
				if not category_name:
					continue
				tags.append(category_name)
			if tags:
				tags = ','.join(tags)
				put_data = {
					'product': {
						'id': product_id,
						'tags': tags
					}
				}
				self.api('products/' + to_str(product_id) + '.json', put_data, 'PUT')
		else:
			for category in convert['categories']:
				category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'])
				category_data = self.api('smart_collections/' + str(category_id) + '.json')
				category_data = json_decode(category_data)
				if category_data.get('smart_collection'):
					tags = to_str(convert['tags']).split(',')
					for rule in category_data['smart_collection']['rules']:
						tags.append(rule['condition'])
					if tags:
						tags = ','.join(tags)
						put_data = {
							'product': {
								'id': product_id,
								'tags': tags
							}
						}
						self.api('products/' + to_str(product_id) + '.json', put_data, 'PUT')
				else:
					if not category_id or ('type' in category and category['type'] == 'smart_category'):
						continue
					cat_post_data = {
						'collect': {
							'collection_id': category_id,
							'product_id': product_id
						}
					}
					self.api('collects.json', cat_post_data, 'Post')
		# end : update cate

		# todo: update product
		get_product = self.api('products/' + to_str(product_import) + '.json')
		if not get_product:
			return response_error(self.console_error("Could not get data from Shopify"))
		product_page = json_decode(get_product)
		if not product_page:
			self.log("Can't get collects data, id_src = " + to_str(product_import), 'get_main')
			return response_error()
		product_data = product_page.get('product')
		if product_data:
			name = convert['name']
			name = to_str(name).replace('/', '-')
			product_post = {
				'product': {
					'id': product_import,
					'title': self.strip_html_tag(name),
				}
			}
			if not convert['status']:
				product_post['product']['status'] = 'draft'
			tags = to_str(convert['tags']).split(',')
			if self._notice['config'].get('smart_collection'):
				for category in convert['categories']:
					category_name = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'], 'code_desc')
					if not category_name:
						continue
					tags.append(category_name)
			if tags:
				tags = ','.join(tags)
				product_post['product']['tags'] = tags

			if not convert['children'] and not convert['options']:
				sale_price = None
				compare_price = None
				if convert.get('special_price', dict()).get('price') and self.to_timestamp(convert['special_price']['start_date']) < time.time() and (self.to_timestamp(convert['special_price']['end_date']) > time.time() or (convert['special_price']['end_date'] == '0000-00-00' or convert['special_price']['end_date'] == '0000-00-00 00:00:00') or convert['special_price']['end_date'] == '' or convert['special_price']['end_date'] == None):
					sale_price = convert['special_price']['price']
					compare_price = convert['price']
				else:
					sale_price = convert['price']
				variants = {
					'variant': {
						'id': product_data['variants'][0]['id'],
						'price': to_str(round(to_decimal(sale_price), 2)),
						'sku': convert['sku'],
					},
				}
				variant_response = self.api('variants/' + to_str(product_data['variants'][0]['id']) + '.json', variants, 'PUT')
			elif convert['children']:
				for child in convert['children']:
					child_id = self.get_map_field_by_src(self.TYPE_CHILD, child['id'], child['code'])
					if child_id:
						inventory_item_ids = self.api('variants/' + to_str(child_id) + '.json', None, 'get')
						inventory_item_ids = json_decode(inventory_item_ids)
						check_response = self.check_response_update(inventory_item_ids, convert, 'aas')
						if check_response['result'] == 'success':
							locations_ids = self.api('inventory_levels.json?inventory_item_ids=' + to_str(inventory_item_ids['variant']['inventory_item_id']), None, 'get')
							locations_ids = json_decode(locations_ids)
							inventory_level_data = {
								'location_id': locations_ids['inventory_levels'][0]['location_id'],
								'inventory_item_id': inventory_item_ids['variant']['inventory_item_id'],
								'available': child['qty']
							}
							self.api('inventory_levels/set.json', inventory_level_data, 'post')

			# product_post['product']['variants'] = variants
			if convert['type'] == 'simple' and convert['qty'] and to_int(convert['qty']) > 0 and product_data['variants'][0]['inventory_management'] == 'shopify':
				location_id = self.get_location_id()
				if location_id:
					inventory_post = {
						'location_id': location_id,
						'inventory_item_id': product_data['variants'][0]['inventory_item_id'],
						'available': to_int(convert['qty']),
					}
					inventory = self.api('inventory_levels/set.json', inventory_post, 'POST')

			response = self.api('products/' + to_str(product_import) + '.json', product_post, 'PUT')
			response = json_decode(response)

			# todo: update seo product
			target = '/products/' + to_str(product_data['handle'])
			get_redirects = self.api('redirects.json?target=' + to_str(target))
			if get_redirects:
				redirects = json_decode(get_redirects)
				redirects_data = redirects.get('redirects')
				if redirects_data:
					for redirect_data in redirects_data:
						self.api('redirects/' + to_str(redirect_data['id']) + '.json', None, 'DELETE')

			if self._notice['config']['seo'] or self._notice['config']['seo_301']:
				list_seo = []
				if 'seo' in convert and convert['seo']:
					handle = product_data['handle']
					for seo_url in convert['seo']:
						path = '/' + seo_url['request_path'].strip('/')
						if path not in list_seo:
							list_seo.append(path)
							seo_data = {
								'redirect': {
									'path': path,
									'target': '/products/' + handle
								}
							}
							self.api('redirects.json', seo_data, 'Post')
		# end: update seo product

		return response_success()


	def update_product_after_demo(self, product_id, convert, product, products_ext):
		if self._notice['config'].get('smart_collection'):
			tags = to_str(convert['tags']).split(',')
			for category in convert['categories']:
				category_name = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'], 'code_desc')
				if not category_name:
					continue
				tags.append(category_name)
			if tags:
				tags = ','.join(tags)
				put_data = {
					'product': {
						'id': product_id,
						'tags': tags
					}
				}
				self.api('products/' + to_str(product_id) + '.json', put_data, 'PUT')
		else:
			for category in convert['categories']:
				category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'])
				# if not category_id:
				#     category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'])
				# if not category_id:
				#     category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'])
				if not category_id or ('type' in category and category['type'] == 'smart_category'):
					continue
				cat_post_data = {
					'collect': {
						'collection_id': category_id,
						'product_id': product_id
					}
				}
				self.api('collects.json', cat_post_data, 'Post')


	def router_product_import(self, convert, product, products_ext):
		return response_success('product_import')


	def before_product_import(self, convert, product, products_ext):
		return response_success()


	def product_import(self, convert, product, products_ext):
		images = list()
		main_image = None
		if not self.strip_html_tag(convert['name']):
			return response_error('import product ' + to_str(convert['id']) + ' false.')
		# main_image = None
		# if convert['thumb_image']['url']:
		# 	main_image = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
		# 	images.append({'src': main_image['url']})
		# for img_src in convert['images']:
		# 	image_process = self.process_image_before_import(img_src['url'], img_src['path'])
		# 	images.append({'src': image_process['url']})
		# Resize Image
		list_image_children = []
		for child in convert['children']:
			if 'thumb_image' in child:
				image_process = self.process_image_before_import(child['thumb_image']['url'], child['thumb_image']['path'])
				if image_process:
					list_image_children.append(image_process['url'])
		if convert['thumb_image']['url']:
			main_image = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
			if main_image['url'] not in list_image_children:
				# if self._notice['src']['config'].get('auth'):
				# 	main_image['url'] = self.join_url_auth(main_image['url'])
				if to_str(self._notice['src']['cart_type']) == 'bigcommerce':
					main_image['url'] = self.URL_PROXY + to_str(main_image['url'])
				image_data = self.resize_image(main_image['url'])
				if image_data:
					image_data['alt'] = to_str(convert['thumb_image']['label'])[:512]
					images.append(image_data)
				else:
					images.append({'src': main_image['url'], 'alt': to_str(convert['thumb_image']['label'])[:512]})
		for img_src in convert['images']:
			if 'status' in img_src and not img_src['status']:
				continue
			image_process = self.process_image_before_import(img_src['url'], img_src['path'])
			if image_process['url'] in list_image_children:
				continue
			if self._notice['src']['config'].get('auth'):
				image_process['url'] = self.join_url_auth(image_process['url'])
			if to_str(self._notice['src']['cart_type']) == 'bigcommerce':
				image_process['url'] = self.URL_PROXY + to_str(image_process['url'])
			image_data = self.resize_image(image_process['url'])
			if image_data:
				image_data['alt'] = to_str(img_src['label'])[:512]
				images.append(image_data)
			else:
				images.append({'src': image_process['url'], 'alt': to_str(img_src['label'])[:512]})
		name = self.strip_html_tag(convert['name'])
		name = to_str(name).replace('/', '-')
		post_data = {
			'product': {
				'title': name[0:255],
				'body_html': to_str(convert['description']) if convert['description'] else to_str(convert['short_description']),
				'vendor': convert['manufacturer']['name'] if convert['manufacturer']['name'] else '',
				'product_type': convert['product_type'] if 'product_type' in convert and self.is_shopify() else '',
				'images': images,
				'created_at': convert['created_at'],
				'updated_at': convert['updated_at']
			}
		}

		if not convert['status']:
			post_data['product']["status"] = 'draft'
		# post_data['product']['published_at'] = None

		if convert['meta_description'] or convert['meta_title']:
			post_data['product']['metafields_global_title_tag'] = convert['meta_title']
			post_data['product']['metafields_global_description_tag'] = convert['meta_description']
		metafields_keys = list()
		post_data['product']['metafields'] = list()
		if convert['attributes']:
			for attribute in convert['attributes']:
				if to_str(attribute['option_name']) == 'Description' or to_str(attribute['option_name']) == 'Short Description' or not attribute['option_name']:
					continue
				option_name = self.convert_attribute_code(attribute['option_name'])
				index = 2
				while option_name in metafields_keys:
					option_name = attribute['option_name'] + '_' + to_str(index) + 'nd'
					index += 1

				if ('is_visible' in attribute and not attribute['is_visible']) or (option_name and len(option_name)) < 3:
					continue
				if option_name[:30] in metafields_keys:
					if attribute['option_code'][:30] not in metafields_keys:
						metafield = {
							'key': attribute['option_code'][:30],
							'value': attribute['option_value_name'] if attribute['option_value_name'] else '',
							'type': attribute.get('option_type', 'multi_line_text_field') if self.is_shopify() and attribute.get('option_type') else 'multi_line_text_field',
							'namespace': attribute.get('namespace', 'global') if self.is_shopify() else 'global'
						}
						post_data['product']['metafields'].append(metafield)
						metafields_keys.append(attribute['option_code'][:30])
				else:
					metafield = {
						'key': option_name[:30],
						'value': attribute['option_value_name'] if attribute['option_value_name'] else '',
						'type': attribute.get('option_type', 'multi_line_text_field') if self.is_shopify() and attribute.get('option_type') else 'multi_line_text_field',
						'namespace': attribute.get('namespace', 'global') if self.is_shopify() else 'global'
					}
					metafields_keys.append(option_name[:30])
					post_data['product']['metafields'].append(metafield)
		# add metafield Dimensions
		if to_decimal(convert['length']) and 'length' not in metafields_keys:
			metafield = {
				'key': 'length',
				'value': to_str(convert['length']),
				'type': 'multi_line_text_field',
				'namespace': 'global'
			}
			post_data['product']['metafields'].append(metafield)
		if to_decimal(convert['width']) and 'width' not in metafields_keys:
			metafield = {
				'key': 'width',
				'value': to_str(convert['width']),
				'type': 'multi_line_text_field',
				'namespace': 'global'
			}
			post_data['product']['metafields'].append(metafield)
		if to_decimal(convert['height']) and 'height' not in metafields_keys:
			metafield = {
				'key': 'height',
				'value': to_str(convert['height']),
				'type': 'multi_line_text_field',
				'namespace': 'global'
			}
			post_data['product']['metafields'].append(metafield)
		if to_decimal(convert['weight']) and 'weight' not in metafields_keys:
			metafield = {
				'key': 'weight',
				'value': to_str(convert['weight']),
				'type': 'multi_line_text_field',
				'namespace': 'global'
			}
			post_data['product']['metafields'].append(metafield)
		option_name = 'short_description'
		index = 2
		while option_name in metafields_keys:
			option_name = 'short_description' + ' ' + to_str(index) + 'nd'
			index += 1
		metafields_keys.append(option_name)
		metafield = {
			'key': option_name[:30],
			'value': convert['short_description'] if convert['short_description'] else '',
			'type': 'multi_line_text_field',
			'namespace': 'global'
		}
		post_data['product']['metafields'].append(metafield)
		tags = to_str(convert['tags']).split(',')
		if self._notice['config'].get('smart_collection'):
			for category in convert['categories']:
				category_name = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'], 'code_desc')
				if not category_name:
					continue
				tags.append(category_name)
		if tags:
			tags = ','.join(tag for tag in tags if tag != '.')
			post_data['product']['tags'] = tags
		response = self.api('products.json', post_data, 'Post')
		response = json_decode(response)
		check_response = self.check_response_import(response, convert, 'product')
		if check_response['result'] != 'success':
			if 'Image' in check_response['msg']:
				del post_data['product']['images']
				response = self.api('products.json', post_data, 'Post')
				response = json_decode(response)
				check_response = self.check_response_import(response, convert, 'product')
				if check_response['result'] != 'success':
					return check_response
			elif 'Exceeded 2 calls per second for api client. Reduce request rates to resume uninterrupted service.' in check_response['msg']:
				self.sleep_time(1)
				response = self.api('products.json', post_data, 'Post')
				response = json_decode(response)
				check_response = self.check_response_import(response, convert, 'product')
				if check_response['result'] != 'success':
					return check_response
			elif 'publications: expected Array to be a Hash' in check_response['msg']:
				self.sleep_time(1)
				response = self.api('products.json', post_data, 'Post')
				response = json_decode(response)
				check_response = self.check_response_import(response, convert, 'product')
				if check_response['result'] != 'success':
					return check_response
			else:
				return check_response

		product_id = response['product']['id']
		handle = response['product'].get('handle')
		if self._notice['config']['img_des'] and post_data['product']['body_html']:
			theme_data = self.get_theme_data()
			if theme_data:
				check = False
				description = post_data['product']['body_html']
				match = re.findall(r"<img[^>]+>", to_str(description))
				links = list()
				if match:
					for img in match:
						img_src = re.findall(r"(src=[\"'](.*?)[\"'])", to_str(img))
						if not img_src:
							continue
						img_src = img_src[0]
						if img_src[1] in links:
							continue
						links.append(img_src[1])
				for link in links:
					# download and replace
					if self._notice['src']['config'].get('auth'):
						link = self.join_url_auth(link)
					if to_int(theme_data['count']) >= 1500:
						theme_data = self.get_theme_data(True)
					if not theme_data:
						break
					if not self.image_exist(link):
						continue
					asset_post = self.process_assets_before_import(url_image = link, path = '', id_theme = theme_data['id'], name_image = convert['code'])
					asset_post = json_decode(asset_post)
					if asset_post and asset_post.get('asset'):
						self.update_theme_data(theme_data['count'])
						check = True
						description = to_str(description).replace(link, asset_post['asset']['public_url'])
				if check:
					product_update = {
						'product': {
							'body_html': description
						}
					}
					res = self.api('products/' + to_str(product_id) + '.json', product_update, 'PUT')

		# cat
		if not self._notice['config'].get('smart_collection'):
			for category in convert['categories']:
				category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'])
				# if not category_id:
				#     category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'])
				# if not category_id:
				#     category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'])
				if not category_id or ('type' in category and category['type'] == 'smart_category'):
					continue
				cat_post_data = {
					'collect': {
						'collection_id': category_id,
						'product_id': product_id
					}
				}
				self.api('collects.json', cat_post_data, 'Post')
		# metafield
		# metafield =dict()
		# for attributes in convert['attributes']:
		# 	metafield = {
		# 		'metafield': {
		# 			#   'id ' : product_id,
		# 			# 'created_at':get_current_time(),
		# 			# 'updated_at':get_current_time(),
		# 			'key': attributes['option_name'],
		# 			'value ': attributes['option_value_name'],
		# 			'namespace': 'inventory',
		# 			# 'owner_id':int(time.time()),
		# 			# 'owner_resource':"product",
		# 			'value_type ': "string"
		# 					}
		#
		# 				}
		#
		#
		# 	meta = self.api("products/" + str(product_id)+ "/metafields.json",metafield,'Post')
		# 	pass
		# variant
		var_post_data = {
			'product': {
				'id': product_id
			}
		}
		sale_price = None
		compare_price = None
		if convert.get('special_price', dict()).get('price') and self.to_timestamp(convert['special_price']['start_date']) < time.time() and (self.to_timestamp(convert['special_price']['end_date']) > time.time() or (convert['special_price']['end_date'] == '0000-00-00' or convert['special_price']['end_date'] == '0000-00-00 00:00:00') or convert['special_price']['end_date'] == '' or convert['special_price']['end_date'] == None):
			sale_price = convert['special_price']['price']
			compare_price = convert['price'] if convert['price'] and round(to_decimal(convert['price']), 2) > round(to_decimal(sale_price), 2) else None
		else:
			sale_price = convert['price']

		img_children = dict()
		ivt_children = dict()
		# if
		if convert['children']:
			_map = dict()
			variants = list()
			options = list()
			index = 1
			options_src = dict()
			count = 0
			option_value_dict = dict()
			for child in convert['children']:
				max_count = len(child['attributes']) if child['attributes'] else 0
				if max_count > count:
					count = max_count
					options_src = child['attributes']
				for option in options_src:
					if option['option_name'] not in option_value_dict:
						option_value_dict[option['option_name']] = dict()
						option_value_dict[option['option_name']][option['option_value_id']] = option['option_value_name']
					elif option['option_value_id'] not in option_value_dict[option['option_name']]:
						option_value_dict[option['option_name']][option['option_value_id']] = option['option_value_name']
			# self.log(option_value_dict, 'options')
			if not count:
				# self.log('Product id ' + to_str(convert['id']) + 'import failed. Please fill out children attributes!', 'product_errors')
				return response_error('Product id ' + to_str(convert['id']) + 'import failed. Please fill out children attributes!', 'product_errors')
			all_option_name = list()
			for option in options_src:
				if index == 4:
					break
				if option['option_name'] in all_option_name:
					continue
				all_option_name.append(option['option_name'])
				_map[get_value_by_key_in_dict(option, 'option_id', option['option_code'])] = index
				option_values = option_value_dict[to_str(option['option_name'])]
				option_target = {
					'product_id': product_id,
					'position': index,
					'name': to_str(option['option_name']).replace('/', '-')
				}
				if option_values:
					option_target['values'] = list()
					for key in sorted(option_values.keys()):
						option_target['values'].append(option_values[key])

				options.append(option_target)
				index += 1
			pos = 1
			number_variant_imported = 0
			# for
			list_variants = list()
			for child in convert['children']:
				if number_variant_imported >= 100:
					break
				if child.get('special_price', dict()).get('price') and self.to_timestamp(convert['special_price']['start_date']) < time.time() and (self.to_timestamp(child['special_price']['end_date']) > time.time() or (child['special_price']['end_date'] == '0000-00-00' or child['special_price']['end_date'] == '0000-00-00 00:00:00') or child['special_price']['end_date'] == '' or child['special_price']['end_date'] == None):
					child_sale_price = child.get('special_price', dict()).get('price')
					child_compare_price = child['price'] if child['price'] and round(to_decimal(child['price']), 2) > round(to_decimal(child_sale_price), 2) else None
				else:
					child_sale_price = child['price']
					child_compare_price = compare_price if compare_price and round(to_decimal(compare_price), 2) > round(to_decimal(child_sale_price), 2) else None
				if 'thumb_image' in child and child['thumb_image']['url']:
					if self._notice['src']['config'].get('auth'):
						child['thumb_image']['url'] = self.join_url_auth(child['thumb_image']['url'])
					img_children[str(pos)] = child['thumb_image']
				ivt_children[str(pos)] = child['qty']

				variant = {
					'product_id': product_id,
					'position': pos,
					'title': to_str(child['name']).replace('/', '-'),
					'sku': child['sku'] if child['sku'] else convert['sku'],
					'price': round(to_decimal(child_sale_price), 2) if to_decimal(child_sale_price) > 0 else 0,
					'compare_at_price': round(to_decimal(child_compare_price), 2) if child_compare_price and round(to_decimal(child_compare_price), 2) != round(to_decimal(child_sale_price), 2) else None,
					'weight': to_decimal(child['weight']) if to_decimal(child['weight']) > 0 else 0,
					'cost': get_value_by_key_in_dict(child, 'cost', None),
					'inventory_policy': 'deny' if child['manage_stock'] else 'continue',
					'inventory_management': 'shopify' if child['manage_stock'] else None,
					'taxable': False
				}
				if child.get('barcode'):
					variant['barcode'] = get_value_by_key_in_dict(child, 'barcode', get_value_by_key_in_dict(child, 'upc', get_value_by_key_in_dict(child, 'ean', '')))
				else:
					variant['barcode'] = get_value_by_key_in_dict(convert, 'barcode', get_value_by_key_in_dict(convert, 'upc', get_value_by_key_in_dict(convert, 'ean', '')))
				pos += 1
				map_current = dict()
				for row in child['attributes']:
					map_current[get_value_by_key_in_dict(row, 'option_id', row['option_code'])] = True

				# diff two dict
				map_empty = _map.copy()
				for option_id, value in map_current.items():
					if option_id in map_empty:
						del map_empty[option_id]
					else:
						map_empty[option_id] = value
				count_attr = 0
				variant_option = dict()
				for row in child['attributes']:
					if get_value_by_key_in_dict(row, 'option_id', row['option_code']) in _map:
						if count_attr >= 3:
							break
						variant['option' + to_str(_map[get_value_by_key_in_dict(row, 'option_id', row['option_code'])])] = row['option_value_name']
						variant_option['option' + to_str(_map[get_value_by_key_in_dict(row, 'option_id', row['option_code'])])] = row['option_value_name']
						count_attr += 1
				if map_empty and len(map_empty):
					for remain_id, value in map_empty.items():
						if type(value) is not bool:
							variant['option' + to_str(value)] = 'No Value'
				if not self.check_variant_exist(variant_option, list_variants):
					variants.append(variant)
					list_variants.append(variant_option)

				number_variant_imported += 1
			# endfor
			var_post_data['product']['variants'] = variants
			var_post_data['product']['options'] = options
			var_response = self.api('products/' + to_str(product_id) + '.json', var_post_data, 'Put')
		elif convert['options']:
			options_src = dict()
			options = list()
			variants = list()
			index = 1
			# for
			for option in convert['options']:
				if index == 4:
					break
				values = list()
				option_value_dict = dict()
				values_option = list()
				if option['values']:
					for value in option['values']:
						if value['id']:
							option_value_dict[value['id']] = value['option_value_name']
						elif value['code']:
							option_value_dict[value['code']] = value['option_value_name']
					for key in sorted(option_value_dict.keys()):
						values_option.append(option_value_dict[key])
					i = 2
					for value in option['values']:
						if 'image' in value and value['image']['url'] and self._notice['src']['config'].get('auth'):
							value['image']['url'] = self.join_url_auth(value['image']['url'])
						if to_str(value['option_value_name']) in values:
							value['option_value_name'] = to_str(value['option_value_name']) + to_str(i)
							i += 1
						values.append(value['option_value_name'])
						opt_val = {
							'option_name': to_str(option['option_name']).replace('/', '-'),
							'option_value_name': value['option_value_name'],
							'price': value['option_value_price'] if to_decimal(value['option_value_price']) > 0 else 0,
							'weight': to_decimal(value['option_value_weight']) + to_decimal(convert['weight']) if 'option_value_weight' in value and to_decimal(value['option_value_weight']) + to_decimal(convert['weight']) > 0 else (to_decimal(convert['weight']) if to_decimal(convert['weight']) > 0 else 0),
							'price_prefix': value['price_prefix'],
							'image': get_value_by_key_in_dict(value, 'image', {'url': '', 'path': ''}),
							'optionid': index,
							'option_value_code': value['option_value_code'],
							'option_value_qty': value['option_value_qty'],
						}
						if get_value_by_key_in_dict(option, 'id', option['option_code']) not in options_src:
							options_src[get_value_by_key_in_dict(option, 'id', option['option_code'])] = list()
						options_src[get_value_by_key_in_dict(option, 'id', option['option_code'])].append(opt_val)

					options.append({
						'name': to_str(option['option_name']).replace('/', '-'),
						'position': index,
						'product_id': product_id,
						'values': values_option
					})

					index += 1
			# endfor

			if options_src:
				combination = self.combination_from_multi_dict(options_src)
				pos = 1
				number_imported = 0
				for row in combination:
					if number_imported > 99:
						break
					variant = {
						'sku': row[0]['option_value_code'] if row[0]['option_value_code'] else convert['sku'],
						'barcode': get_value_by_key_in_dict(convert, 'barcode', get_value_by_key_in_dict(convert, 'upc', get_value_by_key_in_dict(convert, 'ean', ''))),
						'position': pos,
						'inventory_quantity': to_int(row[0]['option_value_qty']) if row[0]['option_value_qty'] else to_int(convert['qty']),
						'inventory_policy': 'deny' if convert['manage_stock'] else 'continue',
						'inventory_management': 'shopify' if convert['manage_stock'] else None,
						'taxable': False
					}
					price = to_decimal(sale_price)
					weight = None
					for val in row:
						if 'image' in val and val['image']['url'] and to_str(pos) not in img_children:
							img_children[str(pos)] = val['image']
						variant['option' + to_str(val['optionid'])] = val['option_value_name']
						price += to_decimal(val['price']) if val['price_prefix'] == '+' else -to_decimal(val['price'])
						weight = val['weight'] if to_decimal(val['weight']) > 0 else 0
					pos += 1
					variant['price'] = round(to_decimal(price), 2) if to_int(to_decimal(price)) > 0 else 0
					variant['compare_at_price'] = round(to_decimal(compare_price), 2) if compare_price and to_decimal(compare_price) > to_decimal(price) else None
					variant['product_id'] = product_id
					variant['weight'] = weight
					variants.append(variant)
					number_imported += 1

			if variants:
				var_post_data['product']['variants'] = variants
				var_post_data['product']['options'] = options
				var_response = self.api('products/' + to_str(product_id) + '.json', var_post_data, 'Put')
			else:  # Option not have values
				id_variant = response['product']['variants'][0]['id']
				ivt_children[str(1)] = convert['qty']
				var_post_data = {
					"variant": {
						'id': id_variant,
						'title': 'Default Title',
						'compare_at_price': round(to_decimal(compare_price), 2) if compare_price and to_decimal(compare_price) > to_decimal(sale_price) else None,
						'price': to_str(round(to_decimal(sale_price), 2)) if to_decimal(sale_price) > 0 else 0,
						'sku': convert['sku'],
						'barcode': get_value_by_key_in_dict(convert, 'barcode', get_value_by_key_in_dict(convert, 'upc', get_value_by_key_in_dict(convert, 'ean', ''))),
						'weight': to_decimal(convert['weight']) if to_decimal(convert['weight']) > 0 else 0,
						'inventory_management': 'shopify' if convert['manage_stock'] else None,
						'cost': get_value_by_key_in_dict(convert, 'cost', None),
						'inventory_policy': 'deny' if convert['manage_stock'] else 'continue',
						'taxable': False
					}
				}
				var_response = self.api('variants/' + to_str(id_variant) + '.json', var_post_data, 'Put')
		else:
			id_variant = response['product']['variants'][0]['id']
			ivt_children[str(1)] = convert['qty']
			var_post_data = {
				"variant": {
					'id': id_variant,
					'title': 'Default Title',
					'compare_at_price': round(to_decimal(compare_price), 2) if compare_price and round(to_decimal(compare_price), 2) > round(to_decimal(sale_price), 2) else None,
					'price': to_str(round(to_decimal(sale_price), 2)) if to_decimal(sale_price) > 0 else 0,
					'sku': convert['sku'],
					'barcode': get_value_by_key_in_dict(convert, 'barcode', get_value_by_key_in_dict(convert, 'upc', get_value_by_key_in_dict(convert, 'ean', ''))),
					'weight': to_decimal(convert['weight']) if to_decimal(convert['weight']) > 0 else 0,
					'inventory_management': 'shopify' if convert['manage_stock'] else None,
					'cost': get_value_by_key_in_dict(convert, 'cost', None),
					'inventory_policy': 'deny' if convert['manage_stock'] else 'continue',
				}
			}
			if self.is_shopify():
				var_post_data['variant']['inventory_policy'] = convert['inventory_policy']
			var_response = self.api('variants/' + to_str(id_variant) + '.json', var_post_data, 'Put')
		# endif
		var_response = json_decode(var_response)
		check_response = self.check_response_import(var_response, convert, 'product')
		if check_response['result'] != 'success':
			return check_response
		variant_id = response['product']['variants'][0]['id']
		if var_response.get('product') and var_response['product'].get('variants'):
			variant_id = var_response['product']['variants'][0]['id']

		value = {
			'handle': handle,
			'variant_id': variant_id
		}
		self.insert_map(self.TYPE_PRODUCT, convert['id'], product_id, convert['code'], None, value = json_encode(value))

		if convert['children'] and var_response['product']['variants']:
			for k, v in enumerate(var_response['product']['variants']):
				self.insert_map(self.TYPE_CHILD, convert['children'][k]['id'], v['id'])

		# add img to each variant
		if img_children and var_response['product']['variants']:
			unq_img_chil = list()
			for k, v in img_children.items():
				full_img = self.process_image_before_import(v['url'], v['path'])
				# if main_image and main_image['url'] == full_img['url']:
				# 	continue
				variant_id = False
				is_dup = False
				for row in var_response['product']['variants']:
					if to_str(row['position']) == k:
						variant_id = row['id']
						break

				if not variant_id:
					continue

				for index, value in enumerate(unq_img_chil):
					if value['img'] == full_img['url']:
						if 'ids' not in unq_img_chil[index]:
							unq_img_chil[index]['ids'] = list()
						unq_img_chil[index]['ids'].append(variant_id)
						is_dup = True
				if not is_dup:
					unq_img_chil.append({
						'ids': [variant_id],
						'img': full_img['url']
					})

			for row in unq_img_chil:
				data_image = {
					'image': {
						'src': row['img'],
						'variant_ids': row['ids']
					}
				}
				self.api('products/' + to_str(product_id) + '/images.json', data_image, 'Post')

		location_id = self.get_location_id()
		if location_id:
			all_vars = var_response['product']['variants'] if ('product' in var_response) and var_response['product'].get('variants') else [var_response.get('variant')]
			if all_vars:
				for row in all_vars:
					for pos, ivt in ivt_children.items():
						if to_str(row['position']) == to_str(pos) and row['inventory_management']:
							ivt_data = {
								'location_id': location_id,
								'inventory_item_id': row['inventory_item_id'],
								'available': min(to_int(ivt), self.MAX_QTY)
							}
							inventory = self.api('inventory_levels/set.json', ivt_data, 'Post')

		# seo
		if self._notice['config']['seo'] or self._notice['config']['seo_301']:
			if 'seo' in convert and convert['seo']:
				list_seo = []
				handle = response['product']['handle']
				for seo_url in convert['seo']:
					path = '/' + seo_url['request_path'].strip('/')
					if path not in list_seo:
						list_seo.append(path)
						seo_data = {
							'redirect': {
								'path': path,
								'target': '/products/' + handle
							}
						}
						self.api('redirects.json', seo_data, 'Post')
					pass

		return response_success(product_id)


	def after_product_import(self, product_id, convert, product, products_ext):
		# self.langify_import(product_id, self.TYPE_PRODUCT, convert)
		return response_success()


	def addition_product_import(self, convert, product, products_ext):
		return response_success()


	# TODO: CUSTOMER
	def prepare_customers_import(self):
		return self


	def prepare_customers_export(self):
		return self


	def get_customers_main_export(self):
		imported = self._notice['process']['customers']['imported']
		limit_data = self._notice['setting']['customers']
		id_src = self._notice['process']['customers']['id_src']
		page_data = math.floor(int(imported) / to_int(limit_data)) + 1
		customers = self.api('customers.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit_data))
		if not customers:
			return response_error(self.console_error("Could not get data from Shopify"))
		customers_page = json_decode(customers)
		return response_success(customers_page['customers'])


	def get_customers_ext_export(self, customers):
		return response_success()


	def convert_customer_export(self, customer, customers_ext):
		customer_data = self.construct_customer()
		customer_data['id'] = customer['id']
		customer_data['username'] = customer['email'] if customer['email'] else to_str(customer['first_name']) + ' ' + to_str(customer['last_name'])
		customer_data['email'] = customer['email']
		customer_data['first_name'] = customer['first_name']
		customer_data['last_name'] = customer['last_name']
		customer_data['is_subscribed'] = customer['accepts_marketing']
		customer_data['active'] = True if customer['state'] == 'enabled' else False
		customer_data['tags'] = customer['tags']
		customer_data['phone'] = customer['phone']
		customer_data['note'] = customer['note']
		customer_data['created_at'] = convert_format_time(''.join(customer['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		customer_data['updated_at'] = convert_format_time(''.join(customer['updated_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')

		for address_src in customer['addresses']:
			address_data = self.construct_customer_address()
			address_data['id'] = address_src['id']
			address_data['first_name'] = address_src['first_name']
			address_data['last_name'] = address_src['last_name']
			address_data['address_1'] = address_src['address1']
			address_data['address_2'] = address_src['address2']
			address_data['city'] = address_src['city']
			address_data['postcode'] = address_src['zip']
			address_data['telephone'] = address_src['phone']
			address_data['company'] = address_src['company']
			if address_src['default']:
				address_data['default']['billing'] = True
				address_data['default']['shipping'] = True

			address_data['country']['country_code'] = address_src['country_code']
			address_data['country']['name'] = address_src['country_name']
			address_data['state']['state_code'] = address_src['province_code']
			address_data['state']['name'] = address_src['province']
			customer_data['address'].append(address_data)

		return response_success(customer_data)


	def get_customer_id_import(self, convert, customer, customers_ext):
		return customer['id']


	def check_customer_import(self, convert, customer, customers_ext):
		return True if self.get_map_field_by_src(self.TYPE_CUSTOMER, convert['id'], convert['code']) else False


	def router_customer_import(self, convert, customer, customers_ext):
		return response_success('customer_import')


	def before_customer_import(self, convert, customer, customers_ext):
		return response_success()


	def customer_import(self, convert, customer, customers_ext):
		address_src = convert['address']
		first_name = convert['first_name'].replace('https://', '').replace('http://', '') if convert['first_name'] else None
		last_name = convert['last_name'].replace('https://', '').replace('http://', '') if convert['last_name'] else None
		cus_data = {
			"first_name": self.strip_html_tag(first_name, True),
			"last_name": self.strip_html_tag(last_name, True),
			"email": convert['email'],
			"verified_email": False,
			"accepts_marketing": True if convert['is_subscribed'] else False,
			"send_email_welcome": False,
			"created_at": convert['created_at'],
			"updated_at": convert['updated_at'],
			# "created_at": convert['created_at'],
			# "updated_at": convert['updated_at'],
			# "state": convert['active'] ? "enabled": "disabled"
		}
		if convert['phone']:
			cus_data['phone'] = convert['phone']
		# if convert['active']:
		# 	cus_data['password'] = 'f8c876613ab86963a77388ff7922c869'
		# 	cus_data['password_confirmation'] = 'f8c876613ab86963a77388ff7922c869'
		tags = convert['tags'] if convert.get('tags') else ''
		if self._notice['src']['customer_group'] and convert['group_id'] and get_value_by_key_in_dict(self._notice['src']['customer_group'], to_str(convert['group_id']), ''):
			tags += ' ,' + get_value_by_key_in_dict(self._notice['src']['customer_group'], to_str(convert['group_id']), '')
		if tags:
			cus_data['tags'] = tags

		if convert.get('note'):
			cus_data['note'] = convert['note']
		cus_addresses = list()
		for address in address_src:
			if not address['country']['country_code'] or not self.check_country_code(address['country']['country_code']):
				continue
			# state_code = {
			# 	'name': get_value_by_key_in_dict(address['state'], 'name', self.get_state_name_by_code(address['state']['state_code'], address['country']['country_code'])),
			# 	'code': address['state']['state_code']
			# }
			# if not state_code['name']:
			# 	state_code['name'] = address['state']['state_code']
			# if not address['state']['state_code']:
			state_code = {
				'name': None,
				'code': None
			}
			if address['state']['name'] or address['state']['state_code']:
				state_code = self.get_province_from_country(address['country']['country_code'], address['state']['name'], address['state']['state_code'])
			cus_address = {
				"address1": self.strip_html_tag(address['address_1'], True),
				"address2": self.strip_html_tag(address['address_2'], True),
				"city": self.strip_html_tag(address['city'], True),
				"province": state_code['name'],
				"province_code": state_code['code'],
				"phone": get_value_by_key_in_dict(address, 'telephone', ''),
				"zip": address['postcode'],
				"last_name": self.strip_html_tag(address['last_name'], True),
				"first_name": self.strip_html_tag(address['first_name'], True),
				"country": address['country']['name'],
				"country_code": address['country']['country_code'],
				"company": get_value_by_key_in_dict(address, 'company', '')
			}
			if address['default']['shipping']:
				cus_address['default'] = True

			cus_addresses.append(cus_address)
		post_data = dict()
		cus_data['addresses_attributes'] = cus_addresses
		post_data['customer'] = cus_data
		response = self.api('customers.json', post_data, 'Post')
		if response:
			response = json_decode(response)
		check_response = self.check_response_import(response, convert, 'customer')
		if check_response['result'] != 'success' and "phone" in check_response['msg'] and cus_data.get('phone'):
			del cus_data['phone']
			post_data['customer'] = cus_data
			response = self.api('customers.json', post_data, 'Post')
			if response:
				response = json_decode(response)
			check_response = self.check_response_import(response, convert, 'customer')

		if check_response['result'] != 'success':
			if 'email' in check_response['msg']:
				check_response['result'] = 'skip'
			return check_response

		id_desc = response['customer']['id']
		self.insert_map(self.TYPE_CUSTOMER, convert['id'], id_desc, convert['code'])
		return response_success(id_desc)


	def after_customer_import(self, customer_id, convert, customer, customers_ext):
		return response_success()


	def addition_customer_import(self, convert, customer, customers_ext):
		return response_success()


	# TODO: ORDER
	def prepare_orders_import(self):
		return self


	def prepare_orders_export(self):
		return self


	def get_orders_main_export(self):
		imported = self._notice['process']['orders']['imported']
		id_src = self._notice['process']['orders']['id_src']
		limit_data = self._notice['setting']['orders']
		page_data = math.floor(int(imported) / to_int(limit_data)) + 1
		orders = self.api('orders.json?since_id=' + to_str(id_src) + '&status=any' + '&limit=' + to_str(limit_data))
		if not orders:
			return response_error(self.console_error("Could not get order data from Shopify"))
		orders_page = json_decode(orders)
		return response_success(orders_page['orders'])


	def get_orders_ext_export(self, orders):
		return response_success()


	def convert_order_export(self, order, orders_ext):
		order_data = self.construct_order()
		order_data['id'] = order['id']
		order_data['order_number'] = order['name']
		order_data['status'] = order['financial_status']
		order_data['tags'] = order['tags']
		order_data['financial_status'] = order['financial_status']
		order_data['fulfillment_status'] = order.get('fulfillment_status', 'fulfilled')
		if order['total_tax']:
			if order['tax_lines']:
				order_data['tax_lines'] = order['tax_lines']
				tax_name = ''
				rate = 0
				for row in order['tax_lines']:
					if tax_name:
						tax_name += '-' + row['title']
					else:
						tax_name = row['title']
					rate += row['rate']

				order_data['tax']['title'] = tax_name
				order_data['tax']['rate'] = rate

			order_data['tax']['amount'] = order['total_tax']

		order_data['discount']['amount'] = order['total_discounts']

		if order['discount_codes']:
			order_data['discount']['code'] = order['discount_codes'][0]['code']
			order_data['discount']['title'] = order['discount_codes'][0]['code']

		if order['shipping_lines']:
			order_data['shipping']['title'] = order['shipping_lines'][0]['title']
			order_data['shipping']['amount'] = order['shipping_lines'][0]['price']

		order_data['subtotal']['amount'] = order['subtotal_price']
		order_data['total']['amount'] = order['total_price']
		order_data['currency'] = order['currency']
		order_data['created_at'] = convert_format_time(''.join(order['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		order_data['updated_at'] = convert_format_time(''.join(order['updated_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')

		order_customer = self.construct_order_customer()
		if 'customer' in order:
			order_customer['id'] = order['customer']['id']
			order_customer['email'] = order['customer']['email']
			order_customer['first_name'] = order['customer']['first_name']
			order_customer['last_name'] = order['customer']['last_name']

		order_data['customer'] = order_customer

		# if 'customer' in order and order['customer']['default_address']:
		if 'customer' in order and 'default_address' in order['customer']:
			order_customer_address = self.construct_order_address()
			order_customer_address['id'] = order['customer']['default_address']['id']
			order_customer_address['first_name'] = order['customer']['default_address']['first_name']
			order_customer_address['last_name'] = order['customer']['default_address']['last_name']
			order_customer_address['address_1'] = order['customer']['default_address']['address1']
			order_customer_address['address_2'] = order['customer']['default_address']['address2']
			order_customer_address['city'] = order['customer']['default_address']['city']
			order_customer_address['country']['name'] = order['customer']['default_address']['country']
			order_customer_address['country']['country_code'] = order['customer']['default_address']['country_code']
			order_customer_address['state']['name'] = order['customer']['default_address']['province']
			order_customer_address['state']['state_code'] = order['customer']['default_address']['province_code']
			order_customer_address['postcode'] = order['customer']['default_address']['zip']
			order_customer_address['telephone'] = order['customer']['default_address']['phone']
			order_customer_address['company'] = order['customer']['default_address']['company']
			order_data['customer_address'] = order_customer_address

		order_billing = self.construct_order_address()
		if 'billing_address' in order:
			order_billing['first_name'] = order['billing_address']['first_name']
			order_billing['last_name'] = order['billing_address']['last_name']
			order_billing['address_1'] = order['billing_address']['address1']
			order_billing['address_2'] = order['billing_address']['address2']
			order_billing['city'] = order['billing_address']['city']
			order_billing['country']['name'] = order['billing_address']['country']
			order_billing['country']['country_code'] = order['billing_address']['country_code']
			order_billing['state']['name'] = order['billing_address']['province']
			order_billing['state']['state_code'] = order['billing_address']['province_code']
			order_billing['postcode'] = order['billing_address']['zip']
			order_billing['telephone'] = order['billing_address']['phone']
			order_billing['company'] = order['billing_address']['company']

		order_data['billing_address'] = order_billing

		order_shipping = self.construct_order_address()
		if 'shipping_address' in order:
			order_shipping['first_name'] = order['shipping_address']['first_name']
			order_shipping['last_name'] = order['shipping_address']['last_name']
			order_shipping['address_1'] = order['shipping_address']['address1']
			order_shipping['address_2'] = order['shipping_address']['address2']
			order_shipping['city'] = order['shipping_address']['city']
			order_shipping['country']['name'] = order['shipping_address']['country']
			order_shipping['country']['country_code'] = order['shipping_address']['country_code']
			order_shipping['state']['name'] = order['shipping_address']['province']
			order_shipping['state']['state_code'] = order['shipping_address']['province_code']
			order_shipping['postcode'] = order['shipping_address']['zip']
			order_shipping['telephone'] = order['shipping_address']['phone']
			order_shipping['company'] = order['shipping_address']['company']

		order_data['shipping_address'] = order_shipping

		if order['payment_gateway_names']:
			order_payment = self.construct_order_payment()
			order_payment['title'] = order['payment_gateway_names'][0]
			order_payment['method'] = order['payment_gateway_names'][0]
			order_data['payment'] = order_payment

		order_items = list()
		for item in order['line_items']:
			order_item = self.construct_order_item()
			order_item['id'] = item['id']
			sub_total = 0
			if 'pre_tax_price' in item:
				sub_total = to_decimal(item['pre_tax_price'])
			elif 'subtotal_price' in item:
				sub_total = to_decimal(item['subtotal_price'])
			order_item['product']['id'] = item['product_id']
			order_item['product']['name'] = item['title']
			order_item['product']['sku'] = item['sku']
			if item.get('variant_id'):
				order_item['variant'] = dict()
				order_item['variant']['id'] = item['variant_id']
				if not order_item['product']['id']:
					try:
						pro_res = self.api(f'variants/{item["variant_id"]}.json')
						pro_data = json_decode(pro_res)
						order_item['product']['id'] = pro_data['variant']['product_id']
					except:
						pass
			order_item['qty'] = item['quantity']
			if order_data.get('check_fulfill'):
				order_item['qty_shipped'] = item['quantity']
			order_item['price'] = item['price']
			order_item['weight'] = item['grams']
			if not sub_total:
				sub_total = to_decimal(item['price']) * to_int(item['quantity'])
			order_item['original_price'] = round(sub_total / to_int(item['quantity']), 2)
			if item['tax_lines']:
				tax_amount = tax_percent = 0
				for row in item['tax_lines']:
					tax_amount += to_decimal(row['price'])
					tax_percent += to_decimal(row['rate'])

				order_item['tax_amount'] = tax_amount
				order_item['tax_percent'] = tax_percent

			if 'properties' in order_item and order_item['properties']:
				order_item_option = list()
				for custom_option in order_item['properties']:
					order_item_option = self.construct_order_item_option()
					order_item_option['option_name'] = custom_option['name']
					order_item_option['option_value_name'] = custom_option['value']
					order_item_option.append(order_item_option)

				order_item['options'] = order_item_option

			order_item['discount_amount'] = item['total_discount']
			order_item['subtotal'] = sub_total
			order_item['total'] = to_decimal(order_item['price']) * to_int(item['quantity']) - to_decimal(order_item['discount_amount'])
			order_items.append(order_item)

		order_data['items'] = order_items
		order_history = self.construct_order_history()
		order_history['comment'] = order['note']
		order_data['history'].append(order_history)
		if 'customer' in order and order['customer']['note']:
			order_history = self.construct_order_history()
			order_history['comment'] = order['customer']['note']
			order_data['history'].append(order_history)
		order_data['taxes_included'] = order.get('taxes_included', False)
		return response_success(order_data)


	def get_order_id_import(self, convert, order, orders_ext):
		return order['id']


	def check_order_import(self, convert, order, orders_ext):
		self.log(convert,'convert')
		order_id = self.get_map_field_by_src(self.TYPE_ORDER, convert['id'], convert['code'])
		if order_id:
			self.api('orders/'+ to_str(order_id)+'.json',None,'DELETE')
			self.select_raw("DELETE FROM migration_map WHERE type = 'order' AND id_src = "+to_str(convert['id']))
		return True if self.get_map_field_by_src(self.TYPE_ORDER, convert['id'], convert['code']) else False


	def router_order_import(self, convert, order, orders_ext):
		return response_success('order_import')


	def before_order_import(self, convert, order, orders_ext):
		return response_success()


	def order_import(self, convert, order, orders_ext):
		check_customer_exists = False
		if convert.get('financial_status'):
			financial_status = convert['financial_status']
		else:
			financial_status = get_value_by_key_in_dict(self._notice['map']['order_status'], to_str(convert['status']), 'voided')
		post_data = {
			'order': {
				'financial_status': financial_status,
				'confirmed': True,
				'total_price': round(to_decimal(convert['total']['amount']), 2),
				'subtotal_price': round(to_decimal(convert['subtotal']['amount']), 2),
				'currency': self._notice['target']['currency_default'],
				# 'created_at': self.shopify_timezone(convert['created_at'] if convert['created_at'] else get_current_time()),
				'processed_at': self.shopify_timezone(convert['created_at'] if convert['created_at'] else get_current_time()),
				'updated_at': self.shopify_timezone(convert['updated_at'] if convert['updated_at'] else get_current_time()),
				'send_receipt': False,
				'send_fulfillment_receipt': False,
				'suppress_notifications': True,
				'taxes_included': convert.get('taxes_included', False)
			}
		}
		if 'tags' in convert and convert['tags']:
			post_data['order']['tags'] = convert['tags']

		if self._notice['config']['pre_ord']:
			order_name = convert['id']
			if convert.get('order_number'):
				order_name = convert['order_number']
			post_data['order']['name'] = order_name

		if post_data['order']['financial_status'] == 'paid' and post_data['order']['total_price'] > 0:
			post_data['order']['transactions'] = [
				{
					'amount': round(to_decimal(post_data['order']['total_price']), 2),
					'kind': 'sale',
					'test': False,
					'status': 'success',
					'processed_at': self.shopify_timezone(convert['created_at'] if convert['created_at'] else get_current_time())
				}
			]

		if convert.get('fulfillment_status'):
			post_data['order']['fulfillment_status'] = convert['fulfillment_status']
		else:
			if isinstance(self._notice['map'].get('order_status_shopify'), list):
				map_value = dict()
				for index, value_map in enumerate(self._notice['map'].get('order_status_shopify')):
					map_value[to_str(index)] = value_map
				if map_value:
					self._notice['map']['order_status_shopify'] = map_value
			if convert['status'] and self._notice['map'].get('order_status_shopify') and convert['status'] in self._notice['map'].get('order_status_shopify'):
				if self._notice['map']['order_status_shopify'][convert['status']] != 'unfulfilled':
					post_data['order']['fulfillment_status'] = self._notice['map']['order_status_shopify'][convert['status']]

		# elif post_data['order']['financial_status'] == 'paid':
		# 	post_data['order']['fulfillment_status'] = 'fulfilled'

		if convert['discount']['amount'] and (abs(to_decimal(convert['discount']['amount'])) > 0):
			post_data['order']['discount_codes'] = list()
			discount_code = dict()
			post_data['order']['total_discounts'] = round(abs(to_decimal(convert['discount']['amount'])), 2)
			discount_code_title = 'dc'
			if convert['discount']['code']:
				discount_code_title = convert['discount']['code']
			elif convert['discount']['title']:
				discount_code_title = convert['discount']['title']
			discount_code['code'] = discount_code_title
			discount_code['amount'] = round(abs(to_decimal(convert['discount']['amount'])), 2)
			discount_code['type'] = ''
			post_data['order']['discount_codes'].append(discount_code)

		if convert['tax']['amount'] and (to_decimal(convert['tax']['amount']) > 0):
			# if convert['tax']['percent']:
			#   post_data['order']['tax_lines'][0]['title'] = convert['tax']['title']
			#   post_data['order']['tax_lines'][0]['rate'] = round(convert['tax']['percent'], 2) < 1 ? round(convert['tax']['percent'], 2): round(
			#	convert['tax']['percent'], 2) / 100
			post_data['order']['total_tax'] = round(to_decimal(convert['tax']['amount']), 2)
			total_ex_tax = to_decimal(convert['total']['amount']) - to_decimal(convert['tax']['amount'])
			rate = 0
			if total_ex_tax > 0:
				rate = round(to_decimal(convert['tax']['amount']) / total_ex_tax, 2)
			elif to_decimal(convert['total']['amount']) > 0:
				rate = round(to_decimal(convert['tax']['amount']) / to_decimal(convert['total']['amount']), 2)
			post_data['order']['tax_lines'] = [{
				'rate': convert['tax']['rate'] if convert['tax'].get('rate') else rate,
				'title': convert['tax']['title'] if convert['tax'].get('title') else 'TAX',
				'price': round(to_decimal(convert['tax']['amount']), 2)
			}]

		if convert['shipping']['amount'] and (to_decimal(convert['shipping']['amount']) > 0):
			post_data['order']['shipping_lines'] = list()
			ship_lines = dict()
			ship_lines['price'] = round(to_decimal(convert['shipping']['amount']), 2)
			ship_lines['title'] = convert['shipping']['title'] if convert['shipping']['title'] else 'Shipping'
			ship_lines['code'] = 'Shipping'
			post_data['order']['shipping_lines'].append(ship_lines)
		else:
			post_data['order']['shipping_lines'] = list()
			ship_lines = dict()
			ship_lines['price'] = 0
			ship_lines['title'] = 'Free Shipping'
			ship_lines['code'] = 'Shipping'
			post_data['order']['shipping_lines'].append(ship_lines)
		if convert['customer'] and (convert['customer']['id'] or convert['customer']['code']):
			customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, convert['customer']['id'], convert['customer']['code'])
		else:
			customer_id = None
		post_data['order']['customer'] = dict()
		if customer_id:
			post_data['order']['customer']['id'] = customer_id
		# post_data['order']['customer']['phone'] = get_value_by_key_in_dict(convert['billing_address'], 'telephone',
		#                                   get_value_by_key_in_dict(convert['shipping_address'], 'telephone', ''))
		else:
			customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, None, convert['customer']['email'])
			if customer_id:
				post_data['order']['customer']['id'] = customer_id
			else:
				customer_data = {
					'first_name': get_value_by_key_in_dict(convert['customer'], 'first_name', get_value_by_key_in_dict(convert['billing_address'], 'first_name', '')),
					'last_name': get_value_by_key_in_dict(convert['customer'], 'last_name', get_value_by_key_in_dict(convert['billing_address'], 'last_name', '')),
					'email': convert['customer']['email'],
					'total_spent': round(to_decimal(convert['total']['amount']), 2),
					# 'phone': get_value_by_key_in_dict(convert['billing_address'], 'telephone', get_value_by_key_in_dict(convert['shipping_address'], 'telephone', ''))
				}
				post_data['order']['customer'] = customer_data
				check_customer_exists = True
		# billstate_code = {
		# 	'name': get_value_by_key_in_dict(convert['billing_address']['state'], 'name', convert['billing_address']['state']['state_code']),
		# 	'code': convert['billing_address']['state']['state_code']
		# }
		# if not convert['billing_address']['state']['state_code']:
		billstate_code = {
			'name': None,
			'code': None,
		}
		if convert['billing_address']['state']['name'] or convert['billing_address']['state']['code']:
			billstate_code = self.get_province_from_country(convert['billing_address']['country']['country_code'], convert['billing_address']['state']['name'], convert['billing_address']['state']['code'])
		billing_data = {
			'first_name': get_value_by_key_in_dict(convert['billing_address'], 'first_name', ''),
			'last_name': get_value_by_key_in_dict(convert['billing_address'], 'last_name', ''),
			'address1': get_value_by_key_in_dict(convert['billing_address'], 'address_1', ''),
			'address2': get_value_by_key_in_dict(convert['billing_address'], 'address_2', ''),
			'city': get_value_by_key_in_dict(convert['billing_address'], 'city', 'City'),
			'province': get_value_by_key_in_dict(convert['billing_address']['state'], 'name', billstate_code['name']),
			'country': get_value_by_key_in_dict(convert['billing_address']['country'], 'name', ''),
			'province_code': get_value_by_key_in_dict(convert['billing_address']['state'], 'code', billstate_code['code']),
			'country_code': get_value_by_key_in_dict(convert['billing_address']['country'], 'country_code', ''),
			'zip': get_value_by_key_in_dict(convert['billing_address'], 'postcode', ''),
			'phone': get_value_by_key_in_dict(convert['billing_address'], 'telephone', ''),
			'name': get_value_by_key_in_dict(convert['billing_address'], 'first_name', '') + ' ' + get_value_by_key_in_dict(convert['billing_address'], 'last_name', ''),
			'latitude': None,
			'longitude': None,
			# convert['billing_address']['fax']),
			'company': get_value_by_key_in_dict(convert['billing_address'], 'company', '')
		}
		# shipstate_code = {
		# 	'name': get_value_by_key_in_dict(convert['shipping_address']['state'], 'name', convert['shipping_address']['state']['state_code']),
		# 	'code': convert['shipping_address']['state']['state_code']
		# }
		# if not convert['billing_address']['state']['state_code']:
		shipstate_code = {
			'name': None,
			'code': None,
		}
		if convert['shipping_address']['state']['name'] or convert['shipping_address']['state']['code']:
			shipstate_code = self.get_province_from_country(convert['shipping_address']['country']['country_code'], convert['shipping_address']['state']['name'], convert['shipping_address']['state']['code'])
		shipping_data = {
			'first_name': get_value_by_key_in_dict(convert['shipping_address'], 'first_name', ''),
			'last_name': get_value_by_key_in_dict(convert['shipping_address'], 'last_name', ''),
			'address1': get_value_by_key_in_dict(convert['shipping_address'], 'address_1', get_value_by_key_in_dict(convert['shipping_address'], 'address_2', '<missing address>')),
			'address2': get_value_by_key_in_dict(convert['shipping_address'], 'address_2', '') if get_value_by_key_in_dict(convert['shipping_address'], 'address_1', False) else '',
			'city': get_value_by_key_in_dict(convert['shipping_address'], 'city', 'City'),
			'province': get_value_by_key_in_dict(convert['shipping_address']['state'], 'name', shipstate_code['name']),
			'country': get_value_by_key_in_dict(convert['shipping_address']['country'], 'name', ''),
			'province_code': get_value_by_key_in_dict(convert['shipping_address']['state'], 'code', shipstate_code['code']),
			'country_code': get_value_by_key_in_dict(convert['shipping_address']['country'], 'country_code', ''),
			'zip': get_value_by_key_in_dict(convert['shipping_address'], 'postcode', ''),
			'phone': get_value_by_key_in_dict(convert['shipping_address'], 'telephone', ''),
			'name': get_value_by_key_in_dict(convert['shipping_address'], 'first_name', '') + ' ' + get_value_by_key_in_dict(convert['shipping_address'], 'last_name', ''),
			'latitude': None,
			'longitude': None,
			# convert['billing_address']['fax']),
			'company': get_value_by_key_in_dict(convert['shipping_address'], 'company', '')
		}
		post_data['order']['billing_address'] = billing_data
		post_data['order']['shipping_address'] = shipping_data
		comment = ''
		for history in convert['history']:
			if history['comment']:
				comment += self.clear_tags(to_str(history['comment']).replace('<br />', '\n'))
		post_data['order']['note'] = comment[:5000]

		order_items = list()
		for row in convert['items']:
			product_id = None
			variant_id = None
			##########
			if row['product']['variation_id']:
				
				variant_id=self.get_map_field_by_src(self.TYPE_CHILD, id_src = row['product']['variation_id'])
				
			if not variant_id:
				if row['product']['id'] or row['product']['code']:
					product = self.select_map(self._migration_id, self.TYPE_PRODUCT, id_src = row['product']['id'], code_src = row['product']['code'])
					if product:
						product_id = product['id_desc']
						value = json_decode(product['value'])
						if value and isinstance(value, dict) and value.get('variant_id'):
							variant_id = value['variant_id']
				if product_id:
					product_info = self.api('products/' + to_str(product_id) + '.json')
					if product_info:
						product_info = json_decode(product_info)
						if isinstance(product_info, dict) and product_info.get('product'):
							variant_id = product_info['product']['variants'][0]['id']
							if row['product'].get('sku'):
								for variant in product_info['product']['variants']:
									if row['product'].get('sku') == variant['sku']:
										variant_id = variant['id']
										break
			# properties = list()
			# for option in row['options']:
			# 	custom_option = {
			# 		'name': option['option_name'],
			# 		'value': option['option_value_name']
			# 	}
			# 	properties.append(custom_option)

			item = {
				'variant_id': variant_id,
				'title': to_str(row['product']['name'])[0:255],
				'price': round(to_decimal(row['price']), 2),
				'quantity': to_int(row['qty']) if to_int(row['qty']) > 0 else 1,
				'sku': row['product']['sku'],
				'product_id': product_id if product_id else None,
				'total_discount': round(to_decimal(row['discount_amount']), 2),
				'variant_title': None,
				'name': row['product']['name'],
				'properties': [],
				'grams': get_value_by_key_in_dict(row, 'weight', '')
			}
			order_items.append(item)
		if not order_items or len(order_items) == 0:
			item = {
				'variant_id': None,
				'title': 'Product Name',
				'price': round(to_decimal(convert['total']['amount']), 2),
				'quantity': 1,
				'sku': 'product-name',
				'product_id': None,
				'total_discount': '0.00',
				'variant_title': None,
				'name': 'Product Name',
				'properties': [],
				'grams': 0
			}
			order_items.append(item)
		post_data['order']['line_items'] = order_items
		response = self.api('orders.json', post_data, 'Post')
		response = json_decode(response)

		retry = 5
		while retry > 0 and response and ('errors' in response):
			retry -= 1
			if isinstance(response['errors'], dict) and 'order' in response['errors'] and response['errors'].get('order'):
				# retry if error Phone is invalid
				if response['errors']['order'] and 'Phone is invalid' in response['errors']['order']:
					self.log(self.warning_import_entity(self.TYPE_ORDER, convert['id'], convert['code'], response['errors']['order'][0]))
					del post_data['order']['phone']
					del post_data['order']['billing_address']['phone']
					del post_data['order']['shipping_address']['phone']

			if isinstance(response['errors'], dict) and 'customer.email_address' in response['errors'] and response['errors']['customer.email_address']:
				# retry if error Email contains an invalid domain name
				if response['errors']['customer.email_address'] and response['errors']['customer.email_address'][0] in [
					'Email contains an invalid domain name', 'Email is invalid', "contains an invalid domain name"]:
					cust_email = post_data['order']['customer'].get('email')
					# replace special characters
					cust_email = re.sub('[^A-Za-z0-9]+', '', to_str(cust_email))
					# convert into @gmail.com
					cust_email = cust_email + "@shopify.com"

					self.log("Retry with " + post_data['order']['customer'].get('email') + " = " + cust_email, "orders_errors")
					post_data['order']['customer']["email"] = cust_email

			if 'Exceeded order API rate limit, please try again in a minute.' in response['errors']:
				self.sleep_time(60)
			# call api again
			response = self.api('orders.json', post_data, 'Post')
			response = json_decode(response)

		check_response = self.check_response_import(response, convert, 'order')
		if check_response['result'] != 'success':
			return check_response

		id_desc = response['order']['id']
		self.insert_map(self.TYPE_ORDER, convert['id'], id_desc, convert['code'])
		# update customer phone
		customer_id = response['order']['customer']['id']
		phone = get_value_by_key_in_dict(convert['billing_address'], 'telephone', get_value_by_key_in_dict(convert['shipping_address'], 'telephone', ''))
		if customer_id:
			if check_customer_exists:
				customer = response['order']['customer']
				additional_data = {
					"map": {
						"src": customer['first_name'] + ' ' + customer['last_name'],
						"target": customer['email']
					}
				}
				self.insert_map(self.TYPE_CUSTOMER, None, customer_id, customer['email'], additional_data = additional_data)
			if phone:
				customer_data = {
					'customer': {
						'phone': phone
					}
				}
				a = self.api('customers/' + str(customer_id) + '.json', customer_data, 'PUT')
		return response_success(id_desc)


	def after_order_import(self, order_id, convert, order, orders_ext):
		return response_success()


	def addition_order_import(self, convert, order, orders_ext):
		return response_success()


	def finish_order_import(self):
		self._allow_clear_warning = True
		self._shopify_countries = dict()
		return response_success()


	# TODO: REVIEW
	def prepare_reviews_import(self):
		file_export = 'reviews.csv'

		if self._notice['config']['add_new'] or self._notice['config'].get('recent'):
			file_export = 'reviews_' + get_current_time('%Y-%m-%d') + '.csv'
		else:
			self.delete_obj(self.TABLE_SHOPIFY_REVIEW, {'migration_id': self._migration_id})
			file_path = get_pub_path() + '/media/' + to_str(self._migration_id)
			if os.path.isdir(file_path):
				shutil.rmtree(file_path)
		self._notice['target']['config']['file_review_export'] = file_export
		shopify_reviews_table = self.reviews_table_construct()
		table_query = self.dict_to_create_table_sql(shopify_reviews_table)
		if table_query['result'] != 'success':
			return error_database()
		self.query_raw(table_query['query'])
		return self


	def prepare_reviews_export(self):
		return self


	def get_reviews_main_export(self):
		recent_condition = ''
		if self._notice['config']['add_new']:
			recent_condition = " id NOT IN (SELECT id_src FROM " + TABLE_MAP + " WHERE type = 'review' and migration_id = " + to_str(self._migration_id) + ") AND "
		where_condition = self.dict_to_where_condition({
			'migration_id': self._migration_id
		})
		id_src = self._notice['process']['reviews']['id_src']
		limit = self._notice['setting']['reviews']
		query = "SELECT * FROM " + self.get_table_name("src_" + self.TABLE_SHOPIFY_REVIEW) + " WHERE " + recent_condition + where_condition + " AND id > " + to_str(id_src) + " ORDER BY id ASC LIMIT " + to_str(limit)
		result = self.select_raw(query)
		if result['result'] != 'success':
			return error_database()
		return result


	def get_reviews_ext_export(self, reviews):
		return response_success()


	def convert_review_export(self, review, reviews_ext):
		review_data = self.construct_review()
		review_data['id'] = review['id']
		review_data['product']['code'] = review['product_handle']
		review_data['customer']['code'] = review['email']
		review_data['customer']['name'] = get_value_by_key_in_dict(review, 'author', '')
		if review['email']:
			customer = self.api('customers.json?email=' + review['email'])
			customer = json_decode(customer)
			if customer and customer.get('customers'):
				review_data['customer']['id'] = customer['customers'][0]['id']
		review_data['title'] = review['title']
		review_data['content'] = review['body']
		review_data['status'] = True if to_str(review['state']) == 'published' else False
		review_data['created_at'] = convert_format_time(review['created_at'])
		review_data['updated_at'] = get_current_time()
		rating = self.construct_review_rating()
		rating['rate_code'] = 'default'
		rating['rate'] = to_int(review['rating'])
		review_data['rating'].append(rating)
		return response_success(review_data)


	def get_review_id_import(self, convert, review, reviews_ext):
		return review['id']


	def check_review_import(self, convert, review, reviews_ext):
		return True if self.get_map_field_by_src(self.TYPE_REVIEW, convert['id'], convert['code']) else False


	def router_review_import(self, convert, review, reviews_ext):
		return response_success('review_import')


	def before_review_import(self, convert, review, reviews_ext):
		return response_success()


	def review_import(self, convert, review, reviews_ext):
		product_handle = False
		response = response_success()
		if convert['product']['id'] or convert['product']['code']:
			product_value = self.get_map_field_by_src(self.TYPE_PRODUCT, convert['product']['id'], convert['product']['code'], 'value')
			product_value_decode = json_decode(product_value)
			if product_value_decode:
				product_handle = product_value_decode['handle']
			else:
				product_handle = product_value
		if not product_handle:
			response['result'] = 'warning'
			response['msg'] = self.warning_import_entity('Review', convert['id'], convert['code'],
			                                             'Product of review does not have handle or does not exist.')
			return response

		customer_email = 'shopify@shopify.com'
		if convert['customer']['id'] or convert['customer']['code']:
			customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, convert['customer']['id'], convert['customer']['code'])
			if customer_id:
				customers = self.api('customers/' + to_str(customer_id) + '.json')
				if customers:
					customers = json_decode(customers)
					if not 'error' in customers:
						customer_email = customers['customer']['email']

		review_data = {
			'migration_id': self._migration_id,
			'product_handle': product_handle,
			'state': 'published' if to_int(convert.get('status', 1)) == 1 else 'approved',
			'rating': self.calculate_average_rating(convert['rating']),
			'title': convert['title'].strip() if to_str(convert['title']).strip() else 'Review',
			'author': convert['customer']['name'].strip() if to_str(convert['customer']['name']).strip() else 'Shopify',
			'email': customer_email,
			'location': None,
			'body': convert['content'].strip() if to_str(convert['content']).strip() else 'Thanks!',
			'reply': None,
			'created_at': convert_format_time(convert['created_at']) if convert['created_at'] and convert['created_at'] != '0000-00-00 00:00:00' and convert['created_at'] != '0000-00-00' else get_current_time(),
			'replied_at': '0000-00-00 00:00:00'
		}
		result = self.insert_obj(self.TABLE_SHOPIFY_REVIEW, review_data)
		if not result:
			return response_warning(self.warning_import_entity('Review', convert['id'], convert['code']))

		return response_success(0)


	def after_review_import(self, review_id, convert, review, reviews_ext):
		return response_success()


	def addition_review_import(self, convert, review, reviews_ext):
		return response_success()


	# TODO: PAGE
	def prepare_pages_import(self):
		return self


	def prepare_pages_export(self):
		return self


	def get_pages_main_export(self):
		imported = self._notice['process']['pages']['imported']
		id_src = self._notice['process']['pages']['id_src']
		limit_data = self._notice['setting']['pages']
		pages = self.api('pages.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit_data))
		if not pages:
			return response_error(self.console_error("Could not get page data from Shopify"))
		pages_page = json_decode(pages)
		return response_success(pages_page['pages'])


	def get_pages_ext_export(self, pages):
		return response_success()


	def convert_page_export(self, page, pages_ext):
		page_data = self.construct_cms_page()
		page_data['id'] = page['id']
		page_data['title'] = page['title']
		page_data['author'] = page['author']
		page_data['short_description'] = ''
		page_data['content'] = to_str(page['body_html']).replace('//cdn.shopify.com', 'http://cdn.shopify.com')
		page_data['url_key'] = page['handle']
		page_data['status'] = True if page['published_at'] else False
		page_data['created_at'] = convert_format_time(''.join(page['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		return response_success(page_data)


	def get_page_id_import(self, convert, page, pages_ext):
		return page['id']


	def check_page_import(self, convert, page, pages_ext):
		return True if self.get_map_field_by_src(self.TYPE_PAGE, convert['id']) else False


	def router_page_import(self, convert, page, pages_ext):
		return response_success('page_import')


	def before_page_import(self, convert, page, pages_ext):
		return response_success()


	def page_import(self, convert, page, pages_ext):
		page_data = {
			'page': {
				"author": "admin",
				'title': convert['title'] if convert.get('title') else "Page {}".format(convert['code'] if convert.get('code') else convert['id']),
				'body_html': convert['content'],
				'published': convert['status'],
				'handle': convert['url_key'] if convert['url_key'] else None,
				'template_suffix': 'contact',
			}
		}
		page_data['page']['metafields'] = list()

		metafield = {
			"key": "page_title",
			"value": convert.get('meta_title', 'meta_title'),
			"type": "multi_line_text_field",
			"namespace": "global"
		}
		metafield1 = {
			"key": "description",
			"value": convert.get('meta_description', 'meta_description'),
			"type": "multi_line_text_field",
			"namespace": "global"
		}
		page_data['page']['metafields'].append(metafield)
		page_data['page']['metafields'].append(metafield1)
		# if convert['status']:
		#	page_data['page']['published_at'] = convert['created_at'] if convert['created_at'] else get_current_time(),
		page_data['page']['body_html'] = self.process_description_before_import(convert, is_page = True)
		response = self.api('pages.json', page_data, 'Post')
		response = json_decode(response)
		if response:
			if 'errors' in response and 'handle' in response['errors'] and 'has already been taken' in response['errors']['handle']:
				page_data['page']['handle'] = None
				response = self.api('pages.json', page_data, 'Post')
				response = json_decode(response)
		check_response = self.check_response_import(response, convert, 'page')
		if check_response['result'] != 'success':
			return check_response

		id_desc = response['page']['id']
		self.insert_map(self.TYPE_PAGE, convert['id'], id_desc, None)

		return response_success(0)


	def after_page_import(self, page_id, convert, page, pages_ext):
		# self.langify_import(page_id, self.TYPE_PAGE, convert)
		return response_success()


	def addition_page_import(self, convert, page, pages_ext):
		return response_success()


	# TODO: BLOCK
	def prepare_blogs_import(self):
		return response_success()


	def prepare_blogs_export(self):
		return self


	def get_blogs_main_export(self):
		imported = self._notice['process']['blogs']['imported']
		id_src = self._notice['process']['blogs']['id_src']
		limit_data = self._notice['setting']['blogs']
		articles = self.api('articles.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit_data))
		if not articles:
			return response_error(self.console_error("Could not get articles data from Shopify"))
		articles_page = json_decode(articles)
		return response_success(articles_page['articles'])


	def get_blogs_ext_export(self, blog):
		extend = list()
		for articles in blog['data']:
			blog_page = self.api("blogs/" + to_str(articles['blog_id']) + ".json")
			if not blog_page:
				return response_error(self.console_error("Could not get data blogs from Shopify"))
			blog_data = json_decode(blog_page)
			extend.append(blog_data['blog'])
		return response_success(extend)


	def convert_blog_export(self, blog, blogs_ext):
		blog_data = self.construct_blog_post()
		blog_data['id'] = blog['id']
		blog_data['title'] = blog['title']
		content = to_str(blog['body_html'])
		content = content.replace('https://cdn.shopify.com', '//cdn.shopify.com').replace('http://cdn.shopify.com', '//cdn.shopify.com').replace('//cdn.shopify.com', 'http://cdn.shopify.com')
		blog_data['content'] = content
		blog_data['short_content'] = blog['summary_html']
		blog_data['url_key'] = blog['handle']
		blog_data['tags'] = blog['tags']
		blog_data['status'] = True if blog['published_at'] else False
		blog_data['created_at'] = convert_format_time(''.join(blog['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z') if blog['created_at'] else get_current_time()
		blog_data['updated_at'] = convert_format_time(''.join(blog['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z') if blog['created_at'] else get_current_time()
		if 'image' in blog:
			blog_data['thumb_image']['label'] = to_str(blog['image']['alt'])[:512]
			blog_data['thumb_image']['url'] = to_str(blog['image']['src']).replace('\n\n', '')
			blog_data['thumb_image']['path'] = ''
		blog_categorys = get_list_from_list_by_field(blogs_ext['data'], 'id', blog['blog_id'])
		if blog_categorys:
			for blog_category in blog_categorys:
				blog_cate = self.construct_blog_category()
				blog_cate['id'] = blog_category['id']
				blog_cate['code'] = blog_category['tags']
				blog_cate['name'] = blog_category['title']
				blog_cate['created_at'] = convert_format_time(''.join(blog_category['created_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z') if blog_category['created_at'] else get_current_time()
				blog_cate['updated_at'] = convert_format_time(''.join(blog_category['updated_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z') if blog_category['created_at'] else get_current_time()
				blog_cate['id_blog'] = blog_category['id']
				blog_cate['url_key'] = blog_category['handle']
				blog_data['categories'].append(blog_cate)
		return response_success(blog_data)


	def get_blog_id_import(self, convert, blog, blogs_ext):
		return blog['id']


	def check_blog_import(self, convert, blog, blogs_ext):
		return True if self.get_map_field_by_src(self.TYPE_POST, convert['id'], convert['code']) else False


	def router_blog_import(self, convert, blog, blogs_ext):
		return response_success('block_import')


	def before_blog_import(self, convert, blog, blogs_ext):
		return response_success()


	def blog_import(self, convert, blog, blogs_ext):
		if not convert['categories']:
			convert['categories'].append(self.construct_blog_category())
		for cate_blog in convert['categories']:
			if not cate_blog['name']:
				cate_blog['name'] = 'Default Blog'
			if not cate_blog['code']:
				cate_blog['code'] = to_str(cate_blog['name']).lower().replace(' ', '-')
			check_blog = self.get_map_field_by_src(self.TYPE_BLOG, cate_blog['id'], cate_blog['code'])
			if not check_blog:
				check_blog = self.get_map_field_by_src(self.TYPE_BLOG, None, cate_blog['code'])
			if not check_blog:
				response = self.check_blog_data(cate_blog['name'])
				check_response = self.check_response_import(response, convert, 'blog')
				if check_response['result'] != 'success':
					return check_response
				blog_id = response['blog']['id']
				blog_code = response['blog']['handle']
				self.insert_map(self.TYPE_BLOG, convert['id'], blog_id, cate_blog['code'])
				check_blog = blog_id

			response = self.process_blog_before_import(convert, check_blog)
			check_response = self.check_response_import(response, convert, 'blog')
			if check_response['result'] != 'success':
				return check_response
			id_desc = response['article']['id']
			if not convert['code']:
				convert['code'] = to_str(convert['title']).lower().replace(' ', '-')
			self.insert_map(self.TYPE_POST, convert['id'], id_desc, convert['code'])
			# for comment in convert['comment']:
			# 	comment_data={
			# 		"comment" :{
			# 			"body": comment['comment'],
			# 			"author": comment['user'],
			# 			"email": comment['email'],
			# 			"blog_id": check_blog,
			# 			"article_id": id_desc
			# 		}
			# 	}
			# 	response = self.api('comments.json', comment_data, 'Post')
			# 	if response:
			# 		response = json_decode(response)
			return response_success(id_desc)


	def after_blog_import(self, blog_id, convert, blog, blogs_ext):
		# self.langify_import(blog_id, self.TYPE_BLOG, convert)
		return response_success()


	def addition_blog_import(self, convert, blog, blogs_ext):
		return response_success()


	# TODO: Coupon
	def prepare_coupons_import(self):
		return response_success()


	def prepare_coupons_export(self):
		return self


	def get_coupons_main_export(self):
		imported = self._notice['process']['coupons']['imported']
		id_src = self._notice['process']['coupons']['id_src']
		limit_data = self._notice['setting']['coupons']
		coupons = self.api('price_rules.json?since_id=' + to_str(id_src) + '&limit=' + to_str(limit_data))
		if not coupons:
			return response_error(self.console_error("Could not get coupon data from Shopify"))
		coupons_page = json_decode(coupons)
		if not coupons_page['price_rules']:
			self._notice['process']['coupons']['imported'] += 4
			return response_error(self.console_error("Could not get coupon data from Shopify"))
		return response_success(coupons_page['price_rules'])


	def get_coupons_ext_export(self, coupons):
		return response_success()


	def convert_coupon_export(self, coupon, coupons_ext):
		coupon_data = self.construct_coupon()
		coupon_data['id'] = coupon['id']
		coupon_data['title'] = coupon['title']
		coupon_data['code'] = coupon['title']
		coupon_data['type'] = self.PERCENT if coupon['value_type'] == 'percentage' else self.FIXED
		coupon_data['usage_limit'] = coupon['usage_limit']
		coupon_data['usage_per_customer'] = 1 if coupon['once_per_customer'] == True else 0
		coupon_data['discount_amount'] = abs(to_decimal(coupon['value']))
		if abs(to_decimal(coupon['value'])) == 100:
			coupon_data['simple_free_shipping'] = 1
		coupon_data['from_date'] = convert_format_time(''.join(coupon['starts_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
		coupon_data['to_date'] = convert_format_time(''.join(coupon['ends_at'].rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z') if coupon['ends_at'] else None
		if coupon['ends_at'] and coupon_data['to_date'] <= get_current_time():
			coupon_data['status'] = False
		# if coupon['prerequisite_customer_ids']:
		#     for coupon_customer_id in coupon['prerequisite_customer_ids']:
		#         coupon_usage_data = self.construct_coupon_usage()
		#         coupon_usage_data['customer_id'] = coupon_customer_id
		#         coupon_data['customer_group'].append(coupon_usage_data)
		if coupon['prerequisite_product_ids']:
			for coupon_product_id in coupon['prerequisite_customer_ids']:
				coupon_usage_data = dict()
				coupon_usage_data['product_id'] = coupon_product_id
				coupon_data['products'].append(coupon_usage_data)
		if coupon['prerequisite_collection_ids']:
			for coupon_product_id in coupon['prerequisite_customer_ids']:
				coupon_usage_data = self.construct_coupon_usage()
				coupon_usage_data['category_id'] = coupon_product_id
				coupon_data['categories'].append(coupon_usage_data)
		if coupon.get('entitled_product_ids'):
			for coupon_product_id in coupon['entitled_product_ids']:
				product_id = coupon_product_id
				coupon_data['products'].append(product_id)
		return response_success(coupon_data)


	def get_coupon_id_import(self, convert, coupon, coupons_ext):
		return coupon['id']


	def check_coupon_import(self, convert, coupon, coupons_ext):
		return True if self.get_map_field_by_src(self.TYPE_COUPON, convert['id'], convert['code']) else False


	def router_coupon_import(self, convert, coupon, coupons_ext):
		return response_success('coupon_import')


	def before_coupon_import(self, convert, coupon, coupons_ext):
		return response_success()


	def coupon_import(self, convert, coupon, coupons_ext):
		title = convert['title']
		if not title:
			title = convert['id'] if convert['id'] else convert['code'] if convert['code'] else to_str(to_int(time.time()))
		coupon_data = {
			'title': title,
			'target_type': 'line_item',
			'target_selection': 'all',
			'allocation_method': 'across',
			'customer_selection': 'all',
			'once_per_customer': True if convert.get('usage_per_customer') else False,
			'value_type': 'percentage' if convert['type'] == self.PERCENT else 'fixed_amount',
			'value': -to_decimal(convert['discount_amount']),
			# 'fixed_amount': -to_decimal(convert['discount_amount']),
			'starts_at': convert['from_date'] if convert['from_date'] else (convert['to_date'] if convert['to_date'] else get_current_time()),
			'ends_at': convert['to_date'] if convert['to_date'] else None,
		}
		if convert.get('usage_limit') and to_int(convert.get('usage_limit')) > 0:
			coupon_data['usage_limit'] = to_int(convert.get('usage_limit')) if to_int(convert.get('usage_limit')) <= 2147483648 else 2147483647
		if convert.get('prerequisite_customer_ids'):
			coupon_data['entitled_collection_ids'] = convert.get('prerequisite_customer_ids')
			coupon_data['customer_selection'] = "prerequisite"
		if convert.get('prerequisite_product_ids'):
			coupon_data['prerequisite_product_ids'] = convert.get('prerequisite_product_ids')
			coupon_data['target_selection'] = 'entitled'
		if convert.get('prerequisite_collection_ids'):
			coupon_data['prerequisite_collection_ids'] = convert.get('prerequisite_collection_ids')
			coupon_data['target_selection'] = 'entitled'
		if convert.get('products'):
			entitled_product_ids = list()
			for product in convert['products']:
				product_import = self.get_map_field_by_src(self.TYPE_PRODUCT, product)
				if product_import:
					entitled_product_ids.append(product_import)
			if entitled_product_ids:
				coupon_data['entitled_product_ids'] = entitled_product_ids
				coupon_data['target_type'] = "line_item"
				coupon_data['target_selection'] = "entitled"
		if convert.get('categories'):
			entitled_categories_ids = list()
			for categories in convert['categories']:
				categories_import = self.get_map_field_by_src(self.TYPE_CATEGORY, categories)
				if categories_import:
					entitled_categories_ids.append(categories_import)
			if entitled_categories_ids:
				coupon_data['entitled_collection_ids'] = entitled_categories_ids
				coupon_data['target_type'] = "line_item"
				coupon_data['target_selection'] = "entitled"
		coupon_post = dict()
		coupon_post['price_rule'] = coupon_data
		response = self.api('price_rules.json', coupon_post, 'Post')
		response = json_decode(response)
		check_response = self.check_response_import(response, convert, 'coupon')
		if check_response['result'] != 'success':
			return check_response

		id_desc = response['price_rule']['id']
		self.insert_map(self.TYPE_COUPON, convert['id'], id_desc, convert['code'])
		return response_success(id_desc)


	def after_coupon_import(self, coupon_id, convert, coupon, coupons_ext):
		if convert.get('code'):
			data = {
				"discount_code": {
					"code": convert.get('code')
				}
			}
			self.api('price_rules/' + to_str(coupon_id) + '/discount_codes.json', data, 'Post')
		return response_success()


	def addition_coupon_import(self, convert, coupon, coupons_ext):
		return response_success()


	def display_finish_target(self):
		parent = super().display_finish_target()
		if parent['result'] != 'success':
			return parent
		if not self._notice['config']['reviews'] or self._notice['mode'] == MIGRATION_DEMO:
			return response_success()
		id_export = self.get_map_field_by_src('export_review', 1)
		if not id_export:
			id_export = 0
		file_path = get_pub_path() + '/media/' + to_str(self._migration_id)
		if not os.path.exists(file_path):
			os.makedirs(file_path, mode = 0o777)
			change_permissions_recursive(file_path, 0x777)
		file_name = 'reviews.csv'
		if self._notice['target']['config'].get('file_review_export'):
			file_name = self._notice['target']['config'].get('file_review_export')
		if self._notice['src'].get('setup_type') == 'file':
			file_name = 'shopify_' + file_name
		check_file_exist = False
		if os.path.isfile(file_path + '/' + file_name):
			check_file_exist = True
		column = ['product_handle', 'state', 'rating', 'title', 'author', 'email', 'location', 'body', 'reply', 'created_at', 'replied_at']
		limit = 200
		with open(file_path + '/' + file_name, mode = 'a') as employee_file:
			employee_writer = csv.writer(employee_file, delimiter = ',', quotechar = '"', quoting = csv.QUOTE_MINIMAL)
			if not check_file_exist:
				employee_writer.writerow(column)
			while True:
				query = "SELECT * FROM " + self.TABLE_SHOPIFY_REVIEW + ' WHERE migration_id = ' + to_str(self._migration_id) + ' AND id > ' + to_str(id_export) + ' LIMIT ' + to_str(limit)
				reviews = self.select_raw(query)
				if reviews['result'] != 'success':
					return response_success()
				if not reviews['data']:
					break
				for data in reviews['data']:
					csv_data = list()
					id_export = data['id']
					for field in column:
						value = data[field]
						if field == 'rating' and not value and to_str(value) != '0':
							value = 5
						csv_data.append(value)
					employee_writer.writerow(csv_data)

				if reviews['data'] and len(reviews['data']) < limit:
					break
		if id_export:
			self.insert_map('export_review', 1, id_export)
		files = []
		# r=root, d=directories, f = files
		check_name = 'reviews'
		if self._notice['src'].get('setup_type') == 'file':
			check_name = 'shopify_' + check_name
		for r, d, f in os.walk(file_path):
			for file in f:
				if '.csv' in file and check_name in file:
					files.append(file)
		self._notice['target']['config']['review_files'] = files
		return response_success()


	# api code
	def get_api_path(self, path, add_version = True):
		path = to_str(path).replace('admin/', '')
		prefix = 'admin'
		if add_version:
			prefix += '/api/' + self.get_version_api()
		path = prefix + '/' + path
		return path


	def get_version_api(self):
		if self._version_api:
			return self._version_api
		year = get_current_time("%Y")
		month = to_int(get_current_time("%m")) - 1
		quarter = (to_int(month) - 1) // 3 + 1
		quarter = 1 if quarter < 1 else quarter
		version_api = (to_int(quarter) - 1) * 3 + 1
		if version_api < 10:
			version_api = "0" + to_str(version_api)
		else:
			version_api = to_str(version_api)

		self._version_api = to_str(year) + "-" + version_api
		return self._version_api


	def api(self, path, data = None, api_type = "get", add_version = True):
		path = self.get_api_path(path, add_version)
		self._clear_entity_warning = self._allow_clear_warning
		self._total_time_sleep = 0
		header = {"Content-Type": "application/json"}
		# time.sleep(1)
		url = self.get_api_url() + '/' + to_str(path).strip('/')
		method = 'request_by_' + to_str(api_type).lower()
		if isinstance(data, dict) or isinstance(data, list):
			data = json.dumps(data)
		api_password = self._notice[self._type]['config']['api']['password'] if self._notice[self._type]['config']['api'].get('password') else self._notice[self._type]['config']['api'].get('token')
		header['X-Shopify-Access-Token'] = api_password
		res = getattr(self, method)(url, data, header)
		retry = 0
		while (json_decode(res) is False) or ('expected Array to be a Hash' in to_str(res)) or self.last_status >= 500:
			retry += 1
			self.sleep_time(20)
			res = getattr(self, method)(url, data, header)
			if retry > 5:
				break
		return res


	# def request_by_post(self, url, data, custom_headers = None, auth = None, retry = 0, proxies = ''):
	# 	timeout = 300
	# 	if not self._notice['running']:
	# 		timeout = 30
	# 	if not custom_headers:
	# 		custom_headers = dict()
	# 		custom_headers['User-Agent'] = self.USER_AGENT
	# 	elif isinstance(custom_headers, dict) and not custom_headers.get('User-Agent'):
	# 		custom_headers['User-Agent'] = self.USER_AGENT
	#
	# 	res = False
	# 	r = None
	# 	try:
	# 		r = requests.post(url, data, headers = custom_headers, auth = auth, timeout = timeout)
	# 		self._last_header = r.headers
	# 		res = r.text
	# 		res_data = json_decode(res)
	# 		if r.headers.get('x-shopify-shop-api-call-limit'):
	# 			res_called_data = r.headers.get('x-shopify-shop-api-call-limit')
	# 			res_called_arr = res_called_data.split('/')
	# 			res_called = to_int(res_called_arr[0])
	# 			rest_max = to_int(res_called_arr[1]) if to_len(res_called_arr) > 0 and to_int(res_called_arr[1]) > 40 else 40
	# 			if rest_max - res_called <= 5:
	# 				self.sleep_time(1)
	# 		else:
	# 			self.sleep_time(1)
	# 		if r.status_code == 429:
	# 			if res_data and res_data.get('errors') and 'Daily variant creation limit reached. Please try again later' in to_str(res_data['errors']):
	# 				msg = 'Url ' + url
	# 				msg += '\n Method: Post'
	# 				msg += '\n Status: ' + to_str(r.status_code) if r else ''
	# 				msg += '\n Data: ' + to_str(data)
	# 				msg += '\n Header: ' + to_str(r.headers)
	# 				msg += '\n Response: ' + to_str(res)
	# 				msg += '\n Error: Daily variant creation limit reached, delay 1day'
	# 				self.log(msg, to_str(self.get_type()) + '_status')
	# 				# self.log('Daily variant creation limit reached, delay 1day', 'delay')
	# 				self.sleep_time(24 * 60 * 60, 'shopify_variant')
	# 				return self.request_by_post(url, data, custom_headers, auth)
	# 		r.raise_for_status()
	# 		if r.status_code > 201:
	# 			msg = 'Url ' + url
	# 			# msg += '\n Retry 5 times'
	# 			msg += '\n Method: Post'
	# 			msg += '\n Status: ' + to_str(r.status_code) if r else ''
	# 			msg += '\n Data: ' + to_str(data)
	# 			msg += '\n Header: ' + to_str(r.headers)
	# 			msg += '\n Response: ' + to_str(res)
	# 			self.log(msg, to_str(self.get_type()) + '_status')
	# 	except requests.exceptions.HTTPError as errh:
	# 		res_data = json_decode(res)
	# 		if res_data and res_data.get('errors'):
	# 			if 'Daily variant creation limit reached. Please try again later' in to_str(res_data['errors']):
	# 				msg = 'Url ' + url
	# 				msg += '\n Method: Post'
	# 				msg += '\n Status: ' + to_str(r.status_code) if r else ''
	# 				msg += '\n Data: ' + to_str(data)
	# 				msg += '\n Header: ' + to_str(r.headers)
	# 				msg += '\n Response: ' + to_str(res)
	# 				msg += '\n Error: Daily variant creation limit reached, delay 1day'
	# 				self.log(msg, to_str(self.get_type()) + '_status')
	# 				# self.log('Daily variant creation limit reached, delay 1day', 'delay')
	# 				self.sleep_time(24 * 60 * 60, 'shopify_variant')
	# 				return self.request_by_post(url, data, custom_headers, auth)
	# 			elif "calls per second for api client. Reduce request rates to resume uninterrupted service" in to_str(res_data['errors']):
	# 				if self._notice['resume']['type'] == 'orders':
	# 					self.log('Exceeded 0 calls per second for api client, delay 1m (affiliate)', 'delay')
	# 					self._allow_clear_warning = False
	# 					self.sleep_time(60, 'shopify_affiliate', warning = True)
	# 				else:
	# 					self.log('Exceeded 0 calls per second for api client, delay 2s', 'delay')
	# 					self.sleep_time(2)
	# 				return self.request_by_post(url, data, custom_headers, auth)
	# 		# else:
	# 		msg = 'Url ' + url
	# 		# msg += '\n Retry 5 times'
	# 		msg += '\n Method: Post'
	# 		msg += '\n Status: ' + to_str(r.status_code) if r else ''
	# 		msg += '\n Data: ' + to_str(data)
	# 		msg += '\n Header: ' + to_str(r.headers)
	# 		msg += '\n Response: ' + to_str(res)
	# 		self.log(msg, to_str(self.get_type()) + '_status')
	# 		# if retry < 5:
	# 		#     retry += 1
	# 		#     time.sleep(self.get_time_retry(retry))
	# 		#     return self.request_by_post(url, data, custom_headers, auth, retry)
	# 		# else:
	# 		# self.log("Http Error:" + to_str(errh) + " : " + to_str(res))
	# 	except requests.exceptions.ConnectionError as errc:
	# 		self.log("Error Connecting:" + to_str(errc) + " : " + to_str(res))
	# 	except requests.exceptions.Timeout as errt:
	# 		self.log("Timeout Error:" + to_str(errt) + " : " + to_str(res))
	# 	except requests.exceptions.RequestException as err:
	# 		self.log("OOps: Something Else" + to_str(err) + " : " + to_str(res))
	# 	return res

	def request_by_method(self, method, url, data, custom_headers = None, auth = None, proxies = ''):
		timeout = 300
		if not self._notice['running']:
			timeout = 30
		if not custom_headers:
			custom_headers = dict()
			custom_headers['User-Agent'] = self.USER_AGENT
		elif isinstance(custom_headers, dict) and not custom_headers.get('User-Agent'):
			custom_headers['User-Agent'] = self.USER_AGENT

		res = False
		r = None
		try:
			if method in ['get', 'delete']:
				r = getattr(requests, method)(url, headers = custom_headers, auth = auth, timeout = timeout)
			else:
				r = getattr(requests, method)(url, data, headers = custom_headers, auth = auth, timeout = timeout)
			self.last_header = r.headers
			self.last_status = r.status_code
			res = r.text
			res_data = json_decode(res)
			if 'x-shopify-shop-api-call-limit' in r.headers._store:
				res_called_data = r.headers._store['x-shopify-shop-api-call-limit'][1]
				res_called_arr = res_called_data.split('/')
				res_called = to_int(res_called_arr[0])
				if isinstance(res_called, int):
					if res_called < 20:
						self.sleep_time(0.01)
					elif res_called < 30:
						self.sleep_time(0.1)
					else:
						self.sleep_time(1)
			else:
				self.sleep_time(1)
			if r.status_code == 403:
				if res_data and res_data.get('errors') and 'This action requires merchant approval for ' in to_str(res_data['errors']):
					self._stop_action = True
					msg = 'Url ' + url
					msg += '\n Method: ' + method
					msg += '\n Status: ' + to_str(r.status_code) if r else ''
					msg += '\n Data: ' + to_str(data)
					msg += '\n Header: ' + to_str(r.headers)
					msg += '\n Response: ' + to_str(res)
					msg += '\n Error: ' + res_data.get('errors')
					self.log(msg, to_str(self.get_type()) + '_status')
					# self.log('Daily variant creation limit reached, delay 1day', 'delay')
					scope = re.findall(r"This action requires merchant approval for ([a-z_]+) scope", res_data.get('errors'))
					msg_scope = ''
					if scope:
						msg_scope = scope[0]
					self.sleep_time(0, 403, True, msg = msg_scope)
					return res

			if r.status_code == 429:
				if res_data and res_data.get('errors') and 'Daily variant creation limit reached. Please try again later' in to_str(res_data['errors']):
					msg = 'Url ' + url
					msg += '\n Method: Post'
					msg += '\n Status: ' + to_str(r.status_code) if r else ''
					msg += '\n Data: ' + to_str(data)
					msg += '\n Header: ' + to_str(r.headers)
					msg += '\n Response: ' + to_str(res)
					msg += '\n Error: Daily variant creation limit reached, delay 1day'
					self.log(msg, to_str(self.get_type()) + '_status')
					# self.log('Daily variant creation limit reached, delay 1day', 'delay')
					self.sleep_time(24 * 60 * 60, 'shopify_variant')
					return self.request_by_method(method, url, data, custom_headers, auth, proxies)
			r.raise_for_status()
			if r.status_code > 201:
				msg = 'Url ' + url
				# msg += '\n Retry 5 times'
				msg += '\n Method: Post'
				msg += '\n Status: ' + to_str(r.status_code) if r else ''
				msg += '\n Data: ' + to_str(data)
				msg += '\n Header: ' + to_str(r.headers)
				msg += '\n Response: ' + to_str(res)
				self.log(msg, to_str(self.get_type()) + '_status')
		except requests.exceptions.HTTPError as errh:
			res_data = json_decode(res)
			if res_data and res_data.get('errors'):
				if 'Daily variant creation limit reached. Please try again later' in to_str(res_data['errors']):
					msg = 'Url ' + url
					msg += '\n Method: Post'
					msg += '\n Status: ' + to_str(r.status_code) if r else ''
					msg += '\n Data: ' + to_str(data)
					msg += '\n Header: ' + to_str(r.headers)
					msg += '\n Response: ' + to_str(res)
					msg += '\n Error: Daily variant creation limit reached, delay 1day'
					self.log(msg, to_str(self.get_type()) + '_status')
					# self.log('Daily variant creation limit reached, delay 1day', 'delay')
					self.sleep_time(24 * 60 * 60, 'shopify_variant')
					return self.request_by_method(method, url, data, custom_headers, auth, proxies)
				elif "calls per second for api client. Reduce request rates to resume uninterrupted service" in to_str(res_data['errors']):
					if self._notice['resume']['type'] == 'orders':
						self.log('Exceeded 0 calls per second for api client, delay 1m (affiliate)', 'delay')
						self._allow_clear_warning = False
						self.sleep_time(60, 'shopify_affiliate', warning = True)
					else:
						self.log('Exceeded 0 calls per second for api client, delay 2s', 'delay')
						self.sleep_time(2)
					return self.request_by_method(method, url, data, custom_headers, auth, proxies)
			# else:
			msg = 'Url ' + url
			# msg += '\n Retry 5 times'
			msg += '\n Method: Post'
			msg += '\n Status: ' + to_str(r.status_code) if r else ''
			msg += '\n Data: ' + to_str(data)
			msg += '\n Header: ' + to_str(r.headers)
			msg += '\n Response: ' + to_str(res)
			self.log(msg, to_str(self.get_type()) + '_status')
		# if retry < 5:
		#     retry += 1
		#     time.sleep(self.get_time_retry(retry))
		#     return self.request_by_post(url, data, custom_headers, auth, retry)
		# else:
		# self.log("Http Error:" + to_str(errh) + " : " + to_str(res))
		except requests.exceptions.ConnectionError as errc:
			self.log("Error Connecting:" + to_str(errc) + " : " + to_str(res))
		except requests.exceptions.Timeout as errt:
			self.log("Timeout Error:" + to_str(errt) + " : " + to_str(res))
		except requests.exceptions.RequestException as err:
			self.log("OOps: Something Else" + to_str(err) + " : " + to_str(res))
		return res


	def get_api_url(self):
		if not self._api_url:
			self._api_url = self.create_api_url()
		return self._api_url


	def create_api_url(self):
		url = urllib.parse.urlparse(self._cart_url)
		# if self._notice[self._type]['config']['api'].get('token', ''):
		# 	api_url = self._cart_url
		# else:
		# 	api_key = self._notice[self._type]['config']['api'].get('api_key', '').strip()
		# 	password = self._notice[self._type]['config']['api'].get('password', '').strip()
		# 	api_url = 'https://' + api_key + ':' + password + '@' + url.netloc
		api_url = self._cart_url
		if 'path' in url:
			api_url = api_url.strip('/') + '/' + url['path'].strip('/')
		return api_url


	def check_response_import(self, response, convert, type = ''):
		id = convert['id'] if convert['id'] else convert['code']
		if not response:
			return response_warning(type + ' id ' + to_str(id) + ' import failed.')
		elif response and 'errors' in response:
			console = list()
			if isinstance(response['errors'], list):
				for error in response['errors']:
					error_messages = ''
					if isinstance(error, list):
						error_messages = ' '.join(error)
					else:
						error_messages = error
					console.append(error_messages)
			if isinstance(response['errors'], dict):
				for key, error in response['errors'].items():
					error_messages = ''
					if isinstance(error, list):
						error_messages = ' '.join(error)
					else:
						error_messages = error
					console.append(key + ': ' + error_messages)
			else:
				console.append(response['errors'])
			console_warning = '::'.join(console)
			return response_warning(type + ' id ' + to_str(id) + ' import failed. Error: ' + console_warning)

		else:
			return response_success()


	def check_response_update(self, response, id, type = ''):
		if not response:
			return response_warning(type + ' id ' + to_str(id) + ' import failed.')
		elif 'errors' in response:
			console = list()
			if isinstance(response['errors'], list):
				for error in response['errors']:
					error_messages = ''
					if isinstance(error, list):
						error_messages = ' '.join(error)
					else:
						error_messages = error
					console.append(error_messages)
			if isinstance(response['errors'], dict):
				for key, error in response['errors'].items():
					error_messages = ''
					if isinstance(error, list):
						error_messages = ' '.join(error)
					else:
						error_messages = error
					console.append(key + ': ' + error_messages)
			else:
				console.append(response['errors'])
			console_warning = '::'.join(console)
			return response_warning(type + ' id ' + to_str(id) + ' import failed. Error: ' + console_warning)
		else:
			return response_success()


	def get_shopify_countries(self):
		if self._shopify_countries:
			return self._shopify_countries
		countries_js = self.request_by_get('https://www.shopify.com/services/countries.json', None, {"Content-Type": "application/json"})
		if not countries_js:
			return dict()
		self._shopify_countries = json_decode(countries_js)
		return self._shopify_countries


	def get_province_from_country(self, country_code, province_name = None, province_code = None):
		result = {
			'name': '',
			'code': ''
		}
		countries_data = self.get_shopify_countries()
		if countries_data:
			for country in countries_data:
				if country['code'] != country_code:
					continue
				country_provinces = list()
				if 'provinces' in country:
					country_provinces = country['provinces']
				if province_name or province_code:
					for p in country_provinces:
						if (to_str(province_name) and (to_str(province_name).lower() in to_str(p['name']).lower() or to_str(p['name']).lower() in to_str(province_name).lower())) or (to_str(province_code) and to_str(province_code).lower() == to_str(p['code']).lower()):
							result = p
							break
				if not result['code'] and country_provinces:
					result = self.py_reset(country_provinces)
				break
		return result


	def check_country_code(self, country_code):
		result = False
		countries_data = self.get_shopify_countries()
		if countries_data:
			for country in countries_data:
				if country['code'] == country_code:
					return True
		return result


	def py_reset(self, tmp):
		return tmp[0]


	def calculate_average_rating(self, rates, default = 'default'):
		rate = get_row_from_list_by_field(rates, 'rate_code', default)
		if rate and 'rate' in rate:
			return rate['rate']
		rate_total = 0
		count = to_len(rates) if to_len(rates) > 0 else 1
		for _rate in rates:
			rate_total = rate_total + to_decimal(_rate['rate'])
		average = to_decimal(rate_total / count)
		if average > 5:
			return 5
		else:
			return math.ceil(average)


	def clear_tags(self, text_src):
		tag_re = re.compile(r'<[^>]+>')
		return tag_re.sub('', to_str(text_src))


	def check_variant_exist(self, variant, variant_list):
		if not variant_list:
			return False
		for variant_row in variant_list:
			check = True
			for key, label in variant_row.items():
				if not label:
					continue
				if variant.get(key) != label:
					check = False
					break
			if check:
				return True
		return False


	# def request_by_post(self, url, data, custom_headers=None, auth=None):
	# 	headers = None
	# 	if custom_headers and isinstance(custom_headers, dict):
	# 		headers = list()
	# 		for key, value in custom_headers.items():
	# 			headers.append(to_str(key + ': ' + value))
	# 	else:
	# 		headers = custom_headers
	# 	try:
	# 		response_head = io.BytesIO()
	# 		c = pycurl.Curl()
	# 		c.setopt(c.URL, url)
	# 		c.setopt(c.WRITEFUNCTION, response_head.write)
	# 		c.setopt(c.HTTPHEADER, headers)
	# 		c.setopt(c.SSL_VERIFYPEER, 0)
	# 		c.setopt(c.USERAGENT, "Mozilla/5.0 (Windows NT 6.1; Win64; x64;en; rv:5.0) Gecko/20110619 Firefox/5.0")
	# 		c.setopt(c.FOLLOWLOCATION, 1)
	# 		if data:
	# 			c.setopt(c.POST, 1)
	# 			if isinstance(data, str):
	# 				c.setopt(pycurl.POSTFIELDS, data)
	# 			else:
	# 				c.setopt(pycurl.POSTFIELDS, urlencode(data))
	# 		c.perform()
	# 		status = c.getinfo(pycurl.HTTP_CODE)
	# 		c.close()
	# 		# if status != 200:
	# 		# 	return False
	# 		res = response_head.getvalue().decode('utf-8')
	# 		response_head.close()
	# 		return res
	# 	except Exception:
	# 		self.log_traceback()
	# 		return False

	def detect_seo(self):
		return 'default_seo'


	def categories_default_seo(self, category, categories_ext):
		result = list()
		type_seo = self.SEO_DEFAULT
		if self._notice['support'].get('seo_301') and self._notice['config'].get('seo_301'):
			type_seo = self.SEO_301

		seo_cate = self.construct_seo_category()
		seo_cate['request_path'] = 'collections/' + category['handle'].strip('/')
		seo_cate['default'] = True
		seo_cate['store_id'] = 1
		seo_cate['type'] = type_seo
		result.append(seo_cate)
		return result


	def products_default_seo(self, product, products_ext):
		result = list()
		type_seo = self.SEO_DEFAULT
		if self._notice['support'].get('seo_301') and self._notice['config'].get('seo_301'):
			type_seo = self.SEO_301

		seo_product = self.construct_seo_product()
		seo_product['request_path'] = 'products/' + product['handle'].strip('/')
		seo_product['default'] = True
		seo_product['store_id'] = 1
		seo_product['type'] = type_seo
		result.append(seo_product)

		pro_to_cat = products_ext['data'][product['id']]['custom_category']
		if pro_to_cat:
			for custom in pro_to_cat:
				seo_product = self.construct_seo_product()
				seo_product['request_path'] = 'collections/' + custom['handle'].strip('/') + '/products/' + product[
					'handle'].strip('/')
				seo_product['default'] = False
				seo_product['store_id'] = 1
				seo_product['type'] = type_seo
				result.append(seo_product)
		pro_to_cat_smart = products_ext['data'][product['id']]['smart_category']
		if pro_to_cat_smart:
			for smart in pro_to_cat_smart:
				seo_product = self.construct_seo_product()
				seo_product['request_path'] = 'collections/' + smart['handle'].strip('/') + '/products/' + product[
					'handle'].strip('/')
				seo_product['default'] = False
				seo_product['store_id'] = 1
				seo_product['type'] = type_seo
				result.append(seo_product)

		return result


	def get_time_retry(self, index):
		if index == 1:
			return 1
		if index == 2:
			return 10
		if index == 3:
			return 30
		if index == 4:
			return 150
		return 1800


	def get_access_scopes(self):
		scope = self.api('oauth/access_scopes.json', add_version = False)
		scope = json_decode(scope)
		if not scope or not scope.get('access_scopes'):
			return list()
		list_access_scopes = list()
		if scope:
			for access_scopes in scope['access_scopes']:
				list_access_scopes.append(access_scopes['handle'])
		return list_access_scopes


	def update_theme_data(self, count):
		count = to_int(count) + 1
		self._theme_data['count'] = count
		self.update_map('themes', 1, None, None, None, count)


	def get_theme_data(self, new_theme = False, is_blog = False, is_page = False):
		if self._theme_data:
			return self._theme_data
		themes = dict()
		if new_theme:
			self.delete_obj(TABLE_MAP, {'migration_id': self._migration_id, 'type': 'themes'})
		else:
			themes = self.select_map(self._migration_id, 'themes', 1)
		if themes:
			self._theme_data['id'] = themes['id_desc']
			self._theme_data['count'] = themes['value']
			return self._theme_data
		theme_data = {
			'theme': {
				'name': 'Litextension image blog description' if is_blog else 'Litextension image page description' if is_page else 'Litextension image description',
				'role': 'unpublished',
				'src': 'http://45.56.66.224/themes.zip'
			}
		}
		response = self.api('themes.json', theme_data, 'POST')
		response = json_decode(response)
		if response and response.get('theme'):
			self._theme_data['id'] = response['theme']['id']
			self._theme_data['count'] = 0
			self.insert_map('themes', 1, response['theme']['id'], None, None, 0)
		return self._theme_data


	def process_blog_before_import(self, convert, blog_id):
		article_data = {
			'title': convert['title'],
			'author': 'admin',
			'tags': convert['tags'],
			'body_html': convert['content'],
			'published_at': convert['created_at'] if convert['created_at'] and convert['status'] else None,
			'handle': convert['url_key'],
			'published': convert['status'],
			'summary_html': convert['short_content'],
		}
		if convert['thumb_image']['url']:
			images = list()
			main_image = None
			if convert['thumb_image']['url']:
				main_image = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
				if self.image_exist(main_image.get('url')):
					image_data = self.resize_image(main_image['url'])
					if image_data:
						images = image_data
					else:
						images = {'src': main_image['url']}
				elif self._notice['src']['config'].get('auth') and main_image.get('url'):
					try:
						images = {'attachment': base64.b64encode(main_image['url'])}
					except:
						images = ''
				else:
					images = ''
			article_data['image'] = images

		article_data['body_html'] = self.process_description_before_import(convert, is_blog = True)
		article_post = dict()
		article_post['article'] = article_data
		response = self.api('blogs/' + to_str(blog_id) + '/articles.json', article_post, 'Post')
		response = json_decode(response)

		if not response.get('article'):
			self.log(response, 'blogs_error')

		# SEO BLOG
		if response['article'].get('handle'):
			article_handle = response['article']['handle']
			get_blog = self.api('blogs/' + to_str(blog_id) + '.json')
			if get_blog:
				blog_page = json_decode(get_blog)
				if not blog_page:
					self.log("Can't get blog data, id_src = " + to_str(blog_id), 'get_main')
				blog_data = blog_page.get('blog')
				blog_handle = blog_data['handle']
				target = '/blogs/' + to_str(blog_handle) + '/' + to_str(article_handle)
				if self._notice['config']['seo'] or self._notice['config']['seo_301']:
					if 'url_key' in convert and convert['url_key']:
						seo_data = {
							'redirect': {
								'path': convert['url_key'],
								'target': target
							}
						}
						self.api('redirects.json', seo_data, 'Post')

		return response


	def check_blog_data(self, name):
		blog_data = {
			'blog': {
				'title': name
			}
		}
		response = self.api('blogs.json', blog_data, 'Post')
		response = json_decode(response)
		return response


	def process_description_before_import(self, convert, is_blog=False, is_page=False):
		description = self.process_description_images_before_import(convert['content'], is_blog, is_page)
		return description


	def process_description_images_before_import(self, description, is_blog=False, is_page=False):
		theme_data = self.get_theme_data(is_blog=is_blog, is_page=is_page)
		if not theme_data:
			theme_data = self.get_theme_data(True, is_blog, is_page)
		match = None
		if description:
			match = re.findall(r"<img[^>]+>", to_str(description))
		links = list()
		if match:
			for img in match:
				img_src = re.findall(r"(src=[\"'](.*?)[\"'])", to_str(img))
				if not img_src:
					continue
				img_src = img_src[0]
				if img_src[1] in links:
					continue
				image_path = img_src[1]
				if self._notice['src']['cart_type'] == 'shopify':
					if ('http' or 'https') not in image_path:
						image_path = 'https://' + to_str(image_path).lstrip('//')
					if '?' in image_path:
						img_path = image_path.split('?')
						image_path = img_path[0]
					if image_path in links:
						continue
				links.append(image_path)
		for link in links:
			# download and replace
			if self._notice['src']['config'].get('auth'):
				link = self.join_url_auth(link)
			if 'count' in theme_data and to_int(theme_data['count']) >= 1500:
				theme_data = self.get_theme_data(True, is_blog, is_page)
			if not theme_data:
				break
			asset_post = self.process_assets_before_import(url_image=link, path='', id_theme=theme_data['id'], name_image=link.split('/')[-1])
			asset_post = json_decode(asset_post)
			if asset_post and 'errors' in asset_post:
				continue
			if asset_post and asset_post.get('asset'):
				self.update_theme_data(theme_data['count'])
				description = to_str(description).replace(link, asset_post['asset']['public_url'])

		return description

	def process_assets_before_import(self, url_image, path='', id_theme=0, name_image='image'):
		data_attachment = None
		if url_image.endswith('/'):
			url_image += name_image + '.jpg'
		url = url_image
		scheme, netloc, url_path, qs, anchor = urllib.parse.urlsplit(url)
		if not netloc:
			url = self._notice['src']['cart_url'].strip('/') + '/' + url.strip('/')
		image_process = self.process_image_before_import(url, path)
		if 'path' in image_process and image_process['path']:
			index_special = image_process['path'].rfind('?')
			image_process['path'] = image_process['path'][:index_special] if index_special > -1 else image_process['path']
		if 'url' in image_process and image_process['url'] and image_process['url'].rfind('?') > -1 and not self.image_exist(image_process['url']):
			image_process['url'] = self.URL_PROXY + image_process['url']
			data_attachment = self.get_as_base64(image_process['url'])
		if data_attachment:
			assets_data = {
				'asset': {
					'key': "assets/" + os.path.basename(image_process['path']),
					'attachment': data_attachment,
				}
			}
		else:
			assets_data = {
				'asset': {
					'key': "assets/" + os.path.basename(image_process['path']),
					'src': image_process['url'],
				}
			}
		asset_post = self.api('themes/' + to_str(id_theme) + '/assets.json', assets_data, 'PUT')
		return asset_post


	def get_as_base64(self, url):
		buffered = BytesIO(requests.get(url).content)
		img_base64 = base64.b64encode(buffered.getvalue())
		return img_base64.decode()


	def image_exist(self, url, **kwargs):
		try:
			exist = requests.get(url, headers = {'User-agent': 'your bot 0.1'})
		except:
			return False
		return exist.status_code == requests.codes.ok


	def manufacturers_table_construct(self):
		return {
			'table': 'manufacturers_table_construct',
			'rows': {
				'id': 'INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY',
				'name': 'VARCHAR(255)',
			},
		}


	def shopify_timezone(self, value):
		if not value:
			return ''
		if self._notice['target']['config'].get('time_zone'):
			value = value + self._notice['target']['config'].get('time_zone')
		return value


	def get_count(self, api):
		count = 0
		page = 1
		count_api = self.api(to_str(api) + '&page=' + to_str(page) + "&limit=100")
		count_api = json_decode(count_api)
		while count_api.get('custom_collections') or count_api.get('smart_collections'):
			count_tmp = 0
			if 'custom_collections' in count_api:
				count_tmp = to_len(count_api['custom_collections'])
			if 'smart_collections' in count_api:
				count_tmp = to_len(count_api['smart_collections'])
			if count_tmp > 0:
				count += count_tmp
				page += 1
			else:
				break
			count_api = self.api(to_str(api) + '&page=' + to_str(page) + "&limit=100")
			count_api = json_decode(count_api)
		return count


	def get_sizes(self, url):
		auth = None
		if self._notice['src']['config'].get('auth'):
			auth = (self._notice['src']['config']['auth']['user'], self._notice['src']['config']['auth']['pass'])
		req = requests.get(url, headers = {'User-Agent': self.USER_AGENT, 'Range': 'bytes'}, auth = auth)
		try:
			file = Image.open(BytesIO(req.content))
			sizes = file.size
			return sizes[0] * sizes[1], sizes
		except Exception as e:
			self.log(e, 'image_error')
			return False, False


	def resize_image(self, url):
		auth = None
		if self._notice['src']['config'].get('auth'):
			auth = (self._notice['src']['config']['auth']['user'], self._notice['src']['config']['auth']['pass'])
		# return None
		url_resize_image = url
		name = os.path.basename(url)
		result = dict()
		result['filename'] = name
		result['attachment'] = ''
		try:
			image_size, wh = self.get_sizes(url)
			if wh:
				w = wh[0]
				h = wh[1]
				if to_decimal(to_decimal(w) * to_decimal(h), 2) > to_decimal(3000 * 3000, 2):
					if to_decimal(w) > to_decimal(h):
						h = 3000 * h / w
						w = 3000
					else:
						w = 3000 * w / h
						h = 3000
				elif self._notice['src']['cart_type'] == 'godaddy' or self._notice['src']['cart_type'] == 'squarespace' or auth:
					pass
				else:
					return None
			else:
				return None
			self.sleep_time(0.4)
			r = requests.get(url, headers = {'User-agent': 'your bot 0.1'}, auth = auth)
			if r.status_code != 200:
				return result
			img = Image.open(io.BytesIO(r.content))  # image extension *.png,*.jpg
			img = ImageOps.exif_transpose(img)
			new_width = to_int(w)
			new_height = to_int(h)
			img = img.resize((new_width, new_height), Image.ANTIALIAS)
			output = io.BytesIO()
			if img.mode != 'RGB':
				img = img.convert('RGB')
			img.save(output, format = 'JPEG')
			im_data = output.getvalue()
			image_data = base64.b64encode(im_data)
			if not isinstance(image_data, str):
				# Python 3, decode from bytes to string
				image_data = image_data.decode()
				result['attachment'] = image_data
				return result
		except:
			self.log(url, 'url_fail')

		return None


	def is_shopify(self):
		if self._notice['src']['cart_type'] == self._notice['target']['cart_type']:
			return True
		return False


	def to_timestamp(self, value, str_format = '%Y-%m-%d %H:%M:%S'):
		try:
			timestamp = to_int(time.mktime(time.strptime(value, str_format)))
			if timestamp:
				return timestamp
			return to_int(time.time())
		except:
			return to_int(time.time())


	def get_location_id(self):
		if self._location_id:
			return self._location_id
		location = self.api('locations.json')
		location = json_decode(location)
		try:
			for location_data in location['locations']:
				if location_data['active'] and not location_data.get('legacy'):
					self._location_id = location_data['id']
			if not self._location_id:
				self._location_id = location['locations'][0]['id']
		except Exception:
			self.log_traceback()
			self._location_id = None
		return self._location_id


	def change_image_decription_category(self, post_data, type_category, category_id, convert):
		res = None
		if self._notice['config']['img_des'] and post_data[type_category]['body_html']:
			theme_data = self.get_theme_data()
			if theme_data:
				check = False
				description = post_data[type_category]['body_html']
				match = re.findall(r"<img[^>]+>", to_str(description))
				links = list()
				if match:
					for img in match:
						img_src = re.findall(r"(src=[\"'](.*?)[\"'])", to_str(img))
						if not img_src:
							continue
						img_src = img_src[0]
						if img_src[1] in links:
							continue
						links.append(img_src[1])
				for link in links:
					# download and replace
					if to_int(theme_data['count']) >= 1500:
						theme_data = self.get_theme_data(True)
					if not theme_data:
						break
					asset_post = self.process_assets_before_import(url_image = link, path = '', id_theme = theme_data['id'], name_image = convert['code'])
					asset_post = json_decode(asset_post)
					if asset_post and asset_post.get('asset'):
						self.update_theme_data(theme_data['count'])
						check = True
						description = to_str(description).replace(link, asset_post['asset']['public_url'])
				if check:
					category_update = {
						type_category: {
							'body_html': description
						}
					}
					res = self.api('' + to_str(type_category) + 's/' + to_str(category_id) + '.json', category_update, 'PUT')
					res = json_decode(res)
		return res


	def validate_cart_url(self):
		return self.validate_shopify_url(self._cart_url)


	def validate_shopify_url(self, cart_url):
		scheme, netloc, path, qs, anchor = urllib.parse.urlsplit(cart_url)
		if not netloc or to_str(netloc)[-(len('.myshopify.com')):].lower() != '.myshopify.com':
			return response_error('Please enter the correct url (https://storeid.myshopify.com)')
		return response_success()


	def get_file_info(self):
		return {
			'reviews': {
				'title': 'Reviews',
				'parents': ['reviews']
			},
		}


	def get_allow_extension(self):
		return ['csv']


	def storage_data(self):
		function_name = self._notice['src']['storage']['function']
		if not function_name:
			return {
				'result': 'success'
			}
		return getattr(self, function_name)()


	def get_upload_file_name(self, upload_name):
		return 'shopify' + upload_name + '.csv'


	def table_construct_name(self, table):
		table_data = {
			'src_' + self.TABLE_SHOPIFY_REVIEW: 'reviews_table_construct',
		}
		return table_data[table] if table in table_data else None


	def display_upload(self, upload_msg):
		file = filter(lambda x: self._notice['src']['config']['file'][x]['upload'] == True, self._notice['src']['config']['file'])
		file = list(file)
		if file:
			for key, upload in self._notice['src']['config']['file'].items():
				if not upload or not upload['upload']:
					continue
				construct = getattr(self, key + '_table_construct')()
				validate = construct.get('validation', list())
				folder_upload = self.get_folder_upload(self._migration_id)
				file_upload = folder_upload + '/' + self.get_upload_file_name(key)
				if os.path.isfile(file_upload):
					title = self.get_title_csv_file(file_upload)
					for row in validate:
						if row not in title:
							upload_msg[key] = {
								'result': 'error',
								'name': '',
								'elm': '#result-upload-' + key,
								'msg': "<div class='uir-warning'> File uploaded has incorrect structure</div>"
							}

		self._notice['src']['storage']['function'] = 'setup_storage_csv'
		return {
			'result': 'success',
			'msg': upload_msg,
			'function': 'setup_storage_csv',
		}


	def setup_storage_csv(self):
		tables = list()
		queries = list()
		creates = [
			'reviews_table_construct',
		]
		for create in creates:
			tables.append(getattr(self, create)())
		for table in tables:
			table_query = self.dict_to_create_table_sql(table)
			if table_query['result'] != 'success':
				return error_database()
			queries.append(table_query['query'])
		for query in queries:
			self.query_raw(query)
		self._notice['src']['storage']['result'] = 'process'
		self._notice['src']['storage']['function'] = 'storage_csv_reviews'
		self._notice['src']['storage']['msg'] = ""
		return self._notice['src']['storage']


	def clear_previous_section(self, file_upload):
		tables = {
			'src_' + self.TABLE_SHOPIFY_REVIEW: 'reviews_table_construct',
		}
		no_clear = {

		}
		for table_name, table_construct in tables.items():
			if file_upload:
				table_construct_data = getattr(self, table_construct)()
				if table_construct_data['file'] in file_upload:
					delete = self.delete_obj(table_name, {
						'migration_id': self._migration_id,
					})
					if not delete:
						return error_database()


	def clear_storage_csv(self):
		pass


	def storage_csv_reviews(self):
		return self.storage_csv_by_type('reviews', 'reviews', False, True)


	def join_url_auth(self, url):
		if not url:
			return url
		auth_user = urllib.parse.quote(to_str(self._notice['src']['config']['auth'].get('user')))
		auth_pass = urllib.parse.quote(to_str(self._notice['src']['config']['auth'].get('pass')))
		scheme, netloc, path, qs, anchor = urllib.parse.urlsplit(url)
		netloc = to_str(auth_user) + ':' + to_str(auth_pass) + '@' + to_str(netloc)
		return to_str(urllib.parse.urlunsplit((scheme, netloc, path, qs, anchor)))


	def format_url(self, url):
		url = super().format_url(url)
		url.strip('[]')
		url_parse = urllib.parse.urlparse(url)
		url = "https://" + url_parse.hostname
		validate = self.validate_shopify_url(url)
		if validate['result'] != 'success':
			detect = self.detect_shopify_url(url)
			if detect['result'] == 'success':
				url = detect['data']
		return url


	def detect_shopify_url(self, url):
		url_admin = url + "/admin"
		try:
			response = requests.get(url_admin, allow_redirects = False)
			if response.status_code == 302:
				redirect_url = response.headers.get('location')
				redirect_url = redirect_url.replace('/admin', '')
				validate = self.validate_shopify_url(redirect_url)
				if validate['result'] == 'success':
					return response_success(redirect_url)
		except Exception:
			pass
		return response_error()


	def validate_api_info(self):
		response = response_error('', '#src-api-error' if self.get_type() == 'src' else '#target-api-error', 'Info incorrect')
		response['elm'] = '#error-api'
		if not isinstance(self._notice[self._type]['config'].get('api'), dict) or (not self._notice[self._type]['config']['api'].get('password') and not self._notice[self._type]['config']['api'].get('token')):
			response['msg'] = 'Please enter the correct Api info'
			return response
		return response_success()

	# Todo import data to Langify App
	TYPE_CHANGE = {
		'category': 'collections',
		'product': 'products',
		'page': 'pages',
		'blog': 'articles'
	}

	def langify_table_construct(self):
		table_name = self.TABLE_SHOPIFY_LANGIFY
		if self.get_type() == 'src':
			table_name = 'src_{}'.format(table_name)
		table_data = {
			'table': table_name,
			'rows': {
				'id': 'BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY',
				'migration_id': 'BIGINT',
				'lang_id': 'TEXT',
				'entity_id': 'TEXT',
				'entity_type': 'TEXT',
				'type': 'TEXT',
				'source': 'LONGTEXT',
				'target': 'LONGTEXT',
			},
			'validation': ['migration_id', 'lang_id', 'entity_id', 'entity_type', 'type', 'source', 'target'],
			'file': table_name,
			'encode': 'ENGINE=InnoDB DEFAULT CHARSET=utf8;'
		}
		return table_name, table_data

	def langify_create_table(self):
		table_name, langify_table = self.langify_table_construct()
		table_query = self.dict_to_create_table_sql(langify_table)
		self.query_raw(table_query['query'])
		return table_name


	def langify_import(self, entity_id, entity_type, convert):
		"""
		Detail
		- entity_id: target id
		- type: data in (TYPE_CATEGORY, TYPE_PRODUCT, TYPE_PAGE, TYPE_BLOG)
		- convert: as you know :))))
		"""

		if not convert.get('languages'):
			return response_success()

		table_name = self.langify_create_table()

		type_change = self.TYPE_CHANGE[entity_type]
		type_change_child = type_change.rstrip(type_change[-1])

		entity_data = json_decode(self.api("{}/{}.json".format(type_change, entity_id)))
		metafields_data = json_decode(self.api("{}/{}/metafields.json".format(type_change, entity_id)))
		if not entity_data or 'errors' in entity_data or not metafields_data or 'errors' in metafields_data:
			return response_error()

		langify_data = list()
		langify_construct_default = {
			'migration_id': self._migration_id,
			'entity_id': entity_id,
			'entity_type': entity_type,
		}
		for lang in list(self._notice['src']['languages'].keys()):
			if lang == self._notice['src']['languages_select'][0] or not convert['languages'].get(lang):
				continue

			lang_data = convert['languages'][lang]
			langify_construct_default['lang_id'] = lang

			if entity_type == self.TYPE_CATEGORY:
				collection = entity_data[type_change_child]
				if collection['title'] and lang_data['name']:
					name_langify = langify_construct_default.copy()
					name_langify['type'] = 'category_title'
					name_langify['source'] = collection['title']
					name_langify['target'] = self.strip_html_tag(lang_data['name'])
					langify_data.append(name_langify)
				if collection['body_html'] and lang_data['description']:
					lang_data_description = self.process_description_images_before_import(lang_data['description'])
					description_langify = langify_construct_default.copy()
					description_langify['type'] = 'category_body_html'
					description_langify['source'] = collection['body_html']
					description_langify['target'] = lang_data_description
					langify_data.append(description_langify)
				if lang_data['meta_description']:
					seo_description = get_row_value_from_list_by_field(metafields_data['metafields'], 'key', 'description_tag', 'value')
					if seo_description:
						lang_data_meta_description = self.process_description_images_before_import(lang_data['meta_description'])
						seo_langify = langify_construct_default.copy()
						seo_langify['type'] = 'category_meta_description'
						seo_langify['source'] = seo_description
						seo_langify['target'] = lang_data_meta_description
						langify_data.append(seo_langify)
			elif entity_type == self.TYPE_PRODUCT:
				product_data = entity_data[type_change_child]

				if product_data['title'] and lang_data['name']:
					name_langify = langify_construct_default.copy()
					name_langify['type'] = 'product_title'
					name_langify['source'] = product_data['title']
					name_langify['target'] = self.strip_html_tag(lang_data['name'])
					langify_data.append(name_langify)

				if product_data['body_html'] and (lang_data['description'] or lang_data['short_description']):
					product_data_description = lang_data['description'] if lang_data['description'] else lang_data['short_description']
					product_data_description = self.process_description_images_before_import(product_data_description)

					description_langify = langify_construct_default.copy()
					description_langify['type'] = 'product_body_html'
					description_langify['source'] = product_data['body_html']
					description_langify['target'] = product_data_description
					langify_data.append(description_langify)

				seo_title = get_row_value_from_list_by_field(metafields_data['metafields'], 'key', 'title_tag', 'value')
				if seo_title and lang_data['meta_title']:
					seo_title_langify = langify_construct_default.copy()
					seo_title_langify['type'] = 'product_seo_title'
					seo_title_langify['source'] = seo_title
					seo_title_langify['target'] = lang_data['meta_title']
					langify_data.append(seo_title_langify)

				seo_description = get_row_value_from_list_by_field(metafields_data['metafields'], 'key', 'description_tag', 'value')
				if seo_description and lang_data['meta_description']:
					lang_data_meta_description = self.process_description_images_before_import(lang_data['meta_description'])
					seo_description_langify = langify_construct_default.copy()
					seo_description_langify['type'] = 'product_seo_description'
					seo_description_langify['source'] = seo_description
					seo_description_langify['target'] = lang_data_meta_description
					langify_data.append(seo_description_langify)
			elif entity_type == self.TYPE_PAGE:
				continue
			elif entity_type == self.TYPE_BLOG:
				continue

		for langify in langify_data:
			self.insert_obj(table_name, langify)
