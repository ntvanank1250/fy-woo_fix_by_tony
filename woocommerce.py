import copy
import csv
import re
from collections import defaultdict
from urllib.parse import unquote

import chardet

from cartmigration.libs.utils import *
from cartmigration.models.cart.wordpress import LeCartWordpress
from cartmigration.models.cart.wp_woocommerce.Base import PluginSupport


class LeCartWoocommerce(LeCartWordpress):
    WARNING_VARIANT_LIMIT = 100

    def __init__(self, data=None):
        super().__init__(data)
        self.product_types = dict()
        self.is_variant_limit = False

    def get_list_enabled_plugin(self):
        active_plugin_v_data = list()
        query_active_plugins = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'active_plugins'"
        }
        active_plugins = self.select_data_connector(query_active_plugins, 'query_active_plugins')

        if active_plugins and active_plugins['data']:
            active_plugin_v = active_plugins['data'][0]['option_value']
            if active_plugin_v:
                active_plugin_v_data = php_unserialize(active_plugin_v)
                if active_plugin_v_data and isinstance(active_plugin_v_data, dict):
                    active_plugin_v_data = list(active_plugin_v_data.values())
        return active_plugin_v_data

    def get_order_status(self):
        """
        Return list of Order status on WooCommerce store.
        """
        order_status_data = dict()

        queries_config = {
            'orders_status': {
                'type': 'select',
                'query': "SELECT DISTINCT(`post_status`) FROM `_DBPRF_posts` WHERE `post_type` = 'shop_order'",
            },

        }

        if self._notice['src']['support'][PluginSupport.plugin_order_status.name]:
            queries_config['orders_status'][
                'query'] = "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'wc_order_status'"

        if self._notice['src']['support'][PluginSupport.custom_order_status.name]:
            queries_config['orders_status'][
                'query'] = "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'wc_custom_statuses' AND `post_status` = 'publish'"

        if self._notice['src']['support'][PluginSupport.yith_woocommerce_custom_order_status_premium.name]:
            queries_config['orders_status'][
                'query'] = "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'yith-wccos-ostatus' AND `post_status` = 'publish'"

        if self._notice['src']['support'][PluginSupport.custom_order_statuses.name]:
            queries_config['custom_order_statuses'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'alg_orders_custom_statuses_array'"
            }
        config_order_status = self.select_multiple_data_connector(queries_config, 'query_active_plugins_order_status')

        if config_order_status and config_order_status['result'] == 'success':
            if config_order_status['data']['orders_status']:
                for order_status_row in config_order_status['data']['orders_status']:

                    if self._notice['src']['support'][PluginSupport.custom_order_status.name]:
                        order_status_id = 'wc-' + to_str(order_status_row['post_name'])
                        order_status_data[order_status_id] = order_status_row['post_title']

                    elif self._notice['src']['support'][PluginSupport.plugin_order_status.name]:
                        order_status_id = 'wc-' + order_status_row['post_name']
                        order_status_data[order_status_id] = order_status_row['post_title']

                    elif self._notice['src']['support'][
                        PluginSupport.yith_woocommerce_custom_order_status_premium.name]:
                        order_status_id = order_status_row['post_name']
                        order_status_data[order_status_id] = order_status_row['post_title']
                    else:
                        order_status_id = order_status_row['post_status']
                        order_status_data[order_status_id] = self.get_order_status_label(
                            order_status_row['post_status'])

                if self._notice['src']['support'][PluginSupport.yith_woocommerce_custom_order_status_premium.name]:
                    order_status_data.update(
                        {
                            'wc-pending': 'Pending payment',
                            'wc-processing': 'Processing',
                            'wc-on-hold': 'On hold',
                            'wc-completed': 'Completed',
                            'wc-cancelled': 'Cancelled',
                            'wc-refunded': 'Refunded',
                            'wc-failed': 'Failed'
                        }
                    )
            elif self._notice['src']['support'][PluginSupport.custom_order_statuses.name] \
                    and config_order_status['data'][PluginSupport.custom_order_statuses.name] \
                    and to_len(config_order_status['data'][PluginSupport.custom_order_statuses.name]):

                data = php_unserialize(
                    config_order_status['data'][PluginSupport.custom_order_statuses.name][0]['option_value'])
                order_status_data = data
            else:
                order_status_data = {
                    'wc-pending': 'Pending payment',
                    'wc-processing': 'Processing',
                    'wc-on-hold': 'On hold',
                    'wc-completed': 'Completed',
                    'wc-cancelled': 'Cancelled',
                    'wc-refunded': 'Refunded',
                    'wc-failed': 'Failed'
                }
            return order_status_data

    def display_config_source(self):
        super().display_config_source()

        self._notice['src']['language_default'] = 1
        self._notice['src']['category_root'] = 1
        storage_cat_data = dict()
        storage_cat_data[self._notice['src']['language_default']] = 0
        self._notice['src']['store_category'] = storage_cat_data
        self._notice['src']['support']['site_map'] = False
        self._notice['src']['support']['category_map'] = False
        self._notice['src']['support']['attribute_map'] = False
        for plug_in in PluginSupport:
            self._notice['src']['support'][plug_in.name] = False

        active_langs = list()
        active_plugin_v_data = self.get_list_enabled_plugin()
        if active_plugin_v_data:
            for plug_in in PluginSupport:
                if any([True for plug in plug_in.value if plug in active_plugin_v_data]):
                    self._notice['src']['support'][plug_in.name] = True

            if self._notice['src']['support'][PluginSupport.wpml.name]:
                query_active_languages = {
                    'type': 'select',
                    'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'icl_sitepress_settings'"
                }
                options_data = self.select_data_connector(query_active_languages, 'query_active_languages')

                if options_data and options_data['data']:
                    option_value = php_unserialize(options_data['data'][0]['option_value'])
                    if option_value and 'default_language' in option_value:
                        self._notice['src']['language_default'] = option_value['default_language']
                        active_langs = option_value['active_languages'].values()
                    else:
                        self._notice['src']['support']['wpml'] = False

        queries_config = {
            'permalink_structure': {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE option_name = 'woocommerce_permalinks' OR option_name = 'category_base'",
            }

        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            queries_config['wpml'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_icl_languages` WHERE code IN " + self.list_to_in_condition(active_langs)

            }
        config = self.select_multiple_data_connector(queries_config, 'config')

        language_data = dict()
        product_base = 'product'
        product_category_base = 'product-category'
        if config and config['result'] == 'success':
            if self._notice['src']['support'][PluginSupport.wpml.name]:
                if PluginSupport.wpml.name in config['data']:
                    if config['data'][PluginSupport.wpml.name]:
                        for lang_row in config['data'][PluginSupport.wpml.name]:
                            lang_id = lang_row["code"]
                            language_data[lang_id] = lang_row['english_name']
                    else:
                        lang_id = 'en'
                        language_data[lang_id] = "Default language"
            else:
                lang_id = 1
                language_data[lang_id] = "Default language"

            if config['data']['permalink_structure']:
                product_base_data = get_row_from_list_by_field(config['data']['permalink_structure'], 'option_name',
                                                               'woocommerce_permalinks')
                if product_base_data:
                    option_value_data = php_unserialize(product_base_data['option_value'])
                    if option_value_data:
                        product_base = get_value_by_key_in_dict(option_value_data, 'product_base', 'product')
                        product_category_base = get_value_by_key_in_dict(option_value_data, 'category_base',
                                                                         'product-category')

        self._notice['src']['config']['category_base'] = product_category_base
        self._notice['src']['config']['product_category_base'] = product_category_base
        self._notice['src']['config']['product_base'] = product_base
        self._notice['src']['support']['language_map'] = True
        self._notice['src']['languages'] = language_data
        self._notice['src']['order_status'] = self.get_order_status()
        self._notice['src']['support']['order_status_map'] = True
        self._notice['src']['support']['country_map'] = False
        self._notice['src']['support']['add_new'] = True
        self._notice['src']['support']['site_map'] = False
        self._notice['src']['support']['customer_group_map'] = False
        self._notice['src']['support']['languages_select'] = True
        self._notice['src']['support']['order_state_map'] = True

        self._notice['src']['support']['seo'] = True
        if self.is_woo2woo():
            self._notice['src']['support']['cus_pass'] = False
        else:
            self._notice['src']['support']['cus_pass'] = True
        self._notice['src']['support']['coupons'] = True
        self._notice['src']['support']['pages'] = True
        self._notice['src']['support']['seo_301'] = True
        self._notice['src']['config']['seo_module'] = self.get_list_seo()
        return response_success()

    def display_config_target(self):
        url_query = self.get_connector_url('query')
        self._notice['target']['language_default'] = 1
        self._notice['target']['category_root'] = 1
        storage_cat_data = dict()
        storage_cat_data[self._notice['target']['language_default']] = 0
        self._notice['target']['store_category'] = storage_cat_data
        self._notice['target']['support']['site_map'] = False
        self._notice['target']['support']['category_map'] = False
        self._notice['target']['support']['attribute_map'] = False
        self._notice['target']['support']['wpml'] = False
        self._notice['target']['support']['wpml_currency'] = False
        self._notice['target']['support']['product_bundle'] = False
        self._notice['target']['support']['yoast_seo'] = False
        self._notice['target']['support']['addons'] = False
        self._notice['target']['support']['customer_point_rewards'] = False
        self._notice['target']['support']['polylang'] = False
        self._notice['target']['support']['user_role_editor'] = False
        self._notice['target']['support']['polylang_product'] = False
        self._notice['target']['support']['polylang_category'] = False
        self._notice['target']['support']['plugin_woo_admin'] = False
        self._notice['target']['support']['custom_order_status'] = False
        self._notice['target']['support']['custom_order_statuses'] = False
        self._notice['target']['support']['yith_woocommerce_custom_order_status_premium'] = False
        self._notice['target']['support']['customer_group_map'] = False
        self._notice['target']['currency_map'] = dict()
        query_active_plugins = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'active_plugins'"
        }
        active_plugins = self.get_connector_data(self.get_connector_url('query'),
                                                 {'query': json.dumps(query_active_plugins)})
        active_langs = list()
        if active_plugins and active_plugins['data']:
            active_plugin = active_plugins['data'][0]
            active_plugin_v = active_plugin['option_value']
            if active_plugin_v:
                active_plugin_v_data = php_unserialize(active_plugin_v)
                if active_plugin_v_data and isinstance(active_plugin_v_data, dict):
                    active_plugin_v_data = list(active_plugin_v_data.values())
                if active_plugin_v_data and "woocommerce-multilingual/wpml-woocommerce.php" in active_plugin_v_data:
                    self._notice['target']['support']['wpml'] = True
                    query_active_languages = {
                        'type': 'select',
                        'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'icl_sitepress_settings'"
                    }
                    options_data = self.get_connector_data(self.get_connector_url('query'),
                                                           {'query': json.dumps(query_active_languages)})
                    if options_data and options_data['data']:
                        option_value = php_unserialize(options_data['data'][0]['option_value'])
                        if option_value and 'default_language' in option_value:
                            self._notice['target']['language_default'] = option_value['default_language']
                            active_langs = option_value['active_languages'].values()

                    query_active_currency = {
                        'type': 'select',
                        'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = '_wcml_settings'"
                    }
                    options_currency_data = self.get_connector_data(self.get_connector_url('query'),
                                                                    {'query': json.dumps(query_active_currency)})
                    if options_currency_data and options_currency_data['data']:
                        currency_value = php_unserialize(options_currency_data['data'][0]['option_value'])
                        if currency_value and 'enable_multi_currency' in currency_value and to_int(
                                currency_value['enable_multi_currency']) >= 2:
                            self._notice['target']['support']['wpml_currency'] = True
                            if 'default_currencies' in currency_value and currency_value['default_currencies']:
                                self._notice['target']['currency_map'] = currency_value['default_currencies']
                        else:
                            self._notice['target']['support']['wpml_currency'] = False
                woo_brands = [
                    {'name': 'woocommerce-brand/main.php'},
                    {'name': 'wc-brand/woocommerce-brand.php'},
                    {'name': 'martfury-addons/martfury-addons.php', 'taxonomy': 'product_brand'},
                    {'name': 'woocommerce-brands/woocommerce-brands.php', 'taxonomy': 'product_brand'},
                    {'name': 'brands-for-woocommerce/woocommerce-brand.php', 'taxonomy': 'berocket_brand'},
                    {'name': 'perfect-woocommerce-brands/main.php', 'taxonomy': 'pwb-brand'},
                    {'name': 'perfect-woocommerce-brands/perfect-woocommerce-brands.php', 'taxonomy': 'pwb-brand'},
                ]
                self._notice['target']['config']['brand_taxonomy'] = 'product_brand'
                for brand in woo_brands:
                    if brand['name'] in active_plugin_v_data:
                        self._notice['target']['support']['plugin_manufacturers'] = True
                        if brand.get('taxonomy'):
                            self._notice['target']['config']['brand_taxonomy'] = brand['taxonomy']
                        break
                # if ('woocommerce-brand/main.php' in active_plugin_v_data) or ("wc-brand/woocommerce-brand.php" in active_plugin_v_data) or ('woocommerce-brands/woocommerce-brands.php' in active_plugin_v_data) or ('brands-for-woocommerce/woocommerce-brand.php' in active_plugin_v_data):
                # 	self._notice['target']['support']['manufacturers'] = True
                if active_plugin_v_data and ((
                                                     "woocommerce-sequential-order-numbers/woocommerce-sequential-order-numbers.php" in active_plugin_v_data) or (
                                                     "custom-order-numbers-for-woocommerce/custom-order-numbers-for-woocommerce.php" in active_plugin_v_data) or (
                                                     "sequential-order-numbers-for-woocommerce/sequential-order-numbers.php" in active_plugin_v_data) or (
                                                     "woocommerce-sequential-order-numbers-pro/woocommerce-sequential-order-numbers-pro.php" in active_plugin_v_data)):
                    self._notice['target']['support']['plugin_pre_ord'] = True
                if active_plugin_v_data and "wordpress-seo/wp-seo.php" in active_plugin_v_data:
                    self._notice['target']['support']['yoast_seo'] = True
                if "themedelights-addons/themedelights-addons.php" in active_plugin_v_data or "woocommerce-product-addons/woocommerce-product-addons.php" in active_plugin_v_data:
                    self._notice['target']['support']['addons'] = True
                if "leurlrewrite/leurlrewrite.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_seo'] = True
                    self._notice['target']['support']['plugin_seo_301'] = True
                if "leprespass/leprespass.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_cus_pass'] = True
                if "woocommerce-admin/woocommerce-admin.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_woo_admin'] = True
                if "user-role-editor/user-role-editor.php" in active_plugin_v_data:
                    self._notice['target']['support']['user_role_editor'] = True
                # query_check_seo = {
                # 	'type': 'select',
                # 	'query': "SHOW TABLES LIKE '_DBPRF_lecm_rewrite';"
                # }
                # check_table_exit = self.select_data_connector(query_check_seo, 'seo')
                # if check_table_exit['result'] == 'success' and to_len(check_table_exit['data']) > 0:
                # self._notice['target']['support']['seo_301'] = True
                if "woo-product-bundle-premium/index.php" in active_plugin_v_data or 'woo-product-bundle/index.php' in active_plugin_v_data:
                    self._notice['target']['support']['product_bundle'] = True
                if "woocommerce-points-and-rewards/woocommerce-points-and-rewards.php" in active_plugin_v_data:
                    self._notice['target']['support']['customer_point_rewards'] = True
                # if 'polylang/polylang.php' in active_plugin_v_data and 'polylang-wc/polylang-wc.php' in active_plugin_v_data:
                if ('polylang-pro/polylang.php' in active_plugin_v_data) or (
                        'polylang/polylang.php' in active_plugin_v_data):
                    self._notice['target']['support']['polylang'] = True
                if 'woocommerce-status-actions/woocommerce-status-actions.php' in active_plugin_v_data:
                    self._notice['target']['support']['custom_order_status'] = True
                if 'custom-order-statuses-woocommerce/custom-order-statuses-for-woocommerce.php' in active_plugin_v_data:
                    self._notice['target']['support']['custom_order_statuses'] = True
                if 'woocommerce-order-status-manager/woocommerce-order-status-manager.php' in active_plugin_v_data:
                    self._notice['target']['support']['plugin_order_status'] = True
                if active_plugin_v_data and 'yith-woocommerce-custom-order-status-premium/init.php' in active_plugin_v_data:
                    self._notice['target']['support']['yith_woocommerce_custom_order_status_premium'] = True
        queries_config = {
            'orders_status': {
                'type': 'select',
                # 'query': "SELECT DISTINCT(`post_status`) FROM `_DBPRF_posts` WHERE `post_type` = 'shop_order'",
                'query': "SELECT * FROM `_DBPRF_term_taxonomy` AS term_taxonomy LEFT JOIN _DBPRF_terms AS terms ON term_taxonomy.term_id = terms.term_id WHERE term_taxonomy.taxonomy = 'shop_order_status'",
            },
            'currency_default': {
                'type': 'select',
                # 'query': "SELECT DISTINCT(`post_status`) FROM `_DBPRF_posts` WHERE `post_type` = 'shop_order'",
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'woocommerce_currency'"

            }
        }
        if self._notice['target']['support']['wpml']:
            queries_config['wpml'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_icl_languages` WHERE code IN " + self.list_to_in_condition(active_langs)
            }
            queries_config['default_lang'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` o LEFT JOIN _DBPRF_icl_languages il ON o.option_value = il.default_locale WHERE o.`option_name` = 'WPLANG' and o.`option_value` != '' "
            }
        if self._notice['target']['support']['polylang']:
            queries_config['polylang'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_terms` as t LEFT JOIN `_DBPRF_term_taxonomy` as tx ON t.term_id = tx.term_id WHERE tx.taxonomy = 'language'"
            }
            queries_config['polylang_categories'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_terms` as t LEFT JOIN `_DBPRF_term_taxonomy` as tx ON t.term_id = tx.term_id WHERE tx.taxonomy = 'term_language'"
            }
        if self._notice['target']['support'].get('plugin_order_status'):
            queries_config['custom_order_status'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'wc_order_status'"
            }
        if self._notice['target']['support']['custom_order_status']:
            queries_config['custom_order_status'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'wc_custom_statuses' AND `post_status` = 'publish'"
            }

        if self._notice['target']['support']['custom_order_statuses']:
            queries_config['custom_order_statuses'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'alg_orders_custom_statuses_array'"
            }

        if self._notice['target']['support']['yith_woocommerce_custom_order_status_premium']:
            queries_config['yith_woocommerce_custom_order_status_premium'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_posts` WHERE `post_type` = 'yith-wccos-ostatus' AND `post_status` = 'publish'"
            }

        if self._notice['target']['support']['user_role_editor']:
            queries_config['user_role_editor'] = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = '" + self._notice['target']['config'][
                    'table_prefix'] + "user_roles'"
            }
        config = self.select_multiple_data_connector(queries_config)
        if 'polylang' in config['data'] and not config['data']['polylang']:
            self._notice['target']['support']['polylang'] = False
        language_data = dict()
        order_status_data = dict()
        polylang_products = dict()
        polylang_categories = dict()
        if config and config['result'] == 'success':
            if config['data'].get('currency_default'):
                self._notice['target']['currency_default'] = config['data']['currency_default'][0]['option_value']
            if self._notice['target']['support']['user_role_editor'] and config['data'].get('user_role_editor'):
                user_role_editor = php_unserialize(config['data']['user_role_editor'][0]['option_value'])
                user_role_data = dict()
                none_select = (
                    'administrator', 'editor', 'author', 'contributor', 'shop_manager', 'wpseo_editor', 'wpseo_manager',
                    'translator')
                for role_code, role_data in user_role_editor.items():
                    if role_code in none_select:
                        continue
                    user_role_data[role_code] = role_data['name']
                if user_role_data:
                    self._notice['target']['support']['customer_group_map'] = True
                    self._notice['target']['customer_group'] = user_role_data
            if self._notice['target']['support'].get('plugin_order_status') and config['data'][
                'custom_order_status'] and to_len(config['data']['custom_order_status']) > 0:
                for order_status_row in config['data']['custom_order_status']:
                    order_status_id = 'wc-' + to_str(order_status_row['post_name'])
                    order_status_data[order_status_id] = order_status_row['post_title']
            elif self._notice['target']['support']['yith_woocommerce_custom_order_status_premium']:
                for order_status_row in config['data']['yith_woocommerce_custom_order_status_premium']:
                    order_status_id = order_status_row['post_name']
                    order_status_data[order_status_id] = order_status_row['post_title']
                order_status_data.update(
                    {
                        'wc-pending': 'Pending payment',
                        'wc-processing': 'Processing',
                        'wc-on-hold': 'On hold',
                        'wc-completed': 'Completed',
                        'wc-cancelled': 'Cancelled',
                        'wc-refunded': 'Refunded',
                        'wc-failed': 'Failed'
                    }
                )
            elif self._notice['target']['support']['custom_order_statuses'] and config['data'][
                'custom_order_statuses'] and to_len(config['data']['custom_order_statuses']):
                data = php_unserialize(config['data']['custom_order_statuses'][0]['option_value'])
                order_status_data = data
            elif config['data']['orders_status'] and to_len(config['data']['orders_status']) > 0:
                for order_status_row in config['data']['orders_status']:
                    order_status_id = 'wc-' + to_str(order_status_row['name']).lower()
                    order_status_data[order_status_id] = order_status_row['name']
            # order_status_id = order_status_row['post_status']
            # order_status_data[order_status_id] = self.get_order_status_label(order_status_row['post_status'])
            else:
                order_status_data = {
                    'wc-pending': 'Pending payment',
                    'wc-processing': 'Processing',
                    'wc-on-hold': 'On hold',
                    'wc-completed': 'Completed',
                    'wc-cancelled': 'Cancelled',
                    'wc-refunded': 'Refunded',
                    'wc-failed': 'Failed'
                }
            if self._notice['target']['support']['wpml']:
                if not self._notice['target']['language_default'] and 'default_lang' in config['data'] and \
                        config['data']['default_lang']:
                    for lang_default_row in config['data']['default_lang']:
                        if lang_default_row['code']:
                            self._notice['target']['language_default'] = lang_default_row['code']

                if 'wpml' in config['data']:
                    if config['data']['wpml']:
                        for lang_row in config['data']['wpml']:
                            lang_id = lang_row["code"]
                            language_data[lang_id] = lang_row['english_name']
                    else:
                        lang_id = 'en'
                        language_data[lang_id] = "Default language"
            elif self._notice['target']['support']['polylang']:
                if not self._notice['target']['language_default'] and 'default_lang' in config['data'] and \
                        config['data']['default_lang']:
                    for lang_default_row in config['data']['default_lang']:
                        if lang_default_row['code']:
                            self._notice['target']['language_default'] = lang_default_row['code']
                if 'polylang' in config['data']:
                    if config['data']['polylang']:
                        self._notice['target']['language_default'] = 'en'
                        for lang_row in config['data']['polylang']:
                            lang_id = lang_row['slug']
                            language_data[lang_id] = lang_row['name']
                            lang_product = lang_row['slug']
                            polylang_products[lang_product] = lang_row['term_taxonomy_id']
                    if config['data']['polylang_categories']:
                        for lang_row in config['data']['polylang_categories']:
                            lang_category = lang_row['slug'].replace('pll_', '')
                            polylang_categories[lang_category] = lang_row['term_taxonomy_id']
                else:
                    lang_id = 'en'
                    language_data[lang_id] = "Default language"
            else:
                lang_id = 1
                language_data[lang_id] = "Default language"
        else:
            order_status_data = {
                'wc-pending': 'Pending payment',
                'wc-processing': 'Processing',
                'wc-on-hold': 'On hold',
                'wc-completed': 'Completed',
                'wc-cancelled': 'Cancelled',
                'wc-refunded': 'Refunded',
                'wc-failed': 'Failed'
            }
            lang_id = 1
            language_data[lang_id] = "Default language"
        self._notice['target']['support']['manufacturers'] = True
        self._notice['target']['support']['check_manufacturers'] = True
        # self._notice['target']['support']['yoast_seo'] = False
        self._notice['target']['support']['pre_ord'] = True
        self._notice['target']['support']['check_pre_ord'] = True
        self._notice['target']['support']['seo'] = True
        self._notice['target']['support']['check_seo'] = True
        self._notice['target']['support']['seo_301'] = True
        self._notice['target']['support']['check_seo_301'] = True
        self._notice['target']['support']['cus_pass'] = True
        self._notice['target']['support']['check_cus_pass'] = True
        self._notice['target']['support']['language_map'] = True
        self._notice['target']['languages'] = language_data
        self._notice['target']['order_status'] = order_status_data
        self._notice['target']['support']['order_status_map'] = True
        self._notice['target']['support']['country_map'] = False
        self._notice['target']['support']['add_new'] = True
        self._notice['target']['support']['coupons'] = True
        self._notice['target']['support']['blogs'] = True
        self._notice['target']['support']['pages'] = True
        self._notice['target']['support']['site_map'] = False
        self._notice['target']['support']['pre_prd'] = False
        self._notice['target']['support']['pre_cus'] = False
        self._notice['target']['support']['img_des'] = True
        self._notice['target']['support']['languages_select'] = True
        self._notice['target']['support']['update_latest_data'] = True
        self._notice['target']['config']['entity_update']['products'] = True
        self._notice['target']['support']['polylang_product'] = polylang_products
        self._notice['target']['support']['polylang_category'] = polylang_categories
        return response_success()

    def get_select_lang(self):
        """
        Choosing which language will be converted and transferred by default.
        If choosing multiple languages, default language will be returned.

        Params: No require
        Return: (string) language code
        """
        selected_lang = self._notice['src']['language_default']
        if len(self._notice['src']['languages_select']) == 1:
            selected_lang = self._notice['src']['languages_select'][0]
        return selected_lang

    def get_query_display_import_source(self, update=False):
        compare_condition = ' > '
        if update:
            compare_condition = ' <= '
        prefix = self._notice['src']['config']['table_prefix']
        if self._notice['src']['config'].get('site_id'):
            prefix = to_str(prefix).replace(to_str(self._notice['src']['config'].get('site_id')) + '_', '')
        queries = {
            'taxes': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'woocommerce_tax_classes'",
            },
            'manufacturers': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_term_taxonomy WHERE (taxonomy = 'product_brand' OR taxonomy = 'brand' OR taxonomy = 'pwb-brand') AND term_id " + compare_condition + to_str(
                    self._notice['process']['manufacturers']['id_src']),
            },
            'categories': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_term_taxonomy WHERE taxonomy = 'product_cat' AND term_id " + compare_condition + to_str(
                    self._notice['process']['categories']['id_src']),
            },
            'products': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'product' AND post_status NOT IN ('inherit','auto-draft') AND ID " + compare_condition + to_str(
                    self._notice['process']['products']['id_src']),
            },
            'customers': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM " + prefix + "users u LEFT JOIN " + prefix + "usermeta um ON u.ID = um.user_id WHERE (um.meta_key = '_DBPRF_capabilities' AND um.meta_value LIKE '%customer%' OR um.meta_value LIKE '%subscriber%') AND u.ID " + compare_condition + to_str(
                    self._notice['process']['customers']['id_src']),
            },
            'orders': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft') AND ID " + compare_condition + to_str(
                    self._notice['process']['orders']['id_src']),
            },
            'reviews': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_comments AS cm,_DBPRF_posts AS p WHERE cm.comment_post_ID = p.ID AND p.post_type = 'product' AND cm.comment_ID " + compare_condition + to_str(
                    self._notice['process']['reviews']['id_src']),
            },
            'pages': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'page' AND ID " + compare_condition + to_str(
                    self._notice['process']['pages']['id_src']),
            },
            'coupons': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'shop_coupon' AND ID " + compare_condition + to_str(
                    self._notice['process']['coupons']['id_src']),

            },
            'blogs': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'post' AND ID " + compare_condition + to_str(
                    self._notice['process']['blogs']['id_src']),

            },
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            queries['categories'] = {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_term_taxonomy tt "
                         "LEFT JOIN _DBPRF_icl_translations il ON tt.term_taxonomy_id = il.element_id "
                         "WHERE il.`element_type` = 'tax_product_cat' "
                         "and il.`language_code` = '" + str(
                    self.get_select_lang()) + "' and tt.taxonomy = 'product_cat' and tt.term_taxonomy_id " + compare_condition + to_str(
                    self._notice['process']['categories']['id_src']),
            }
            queries['products'] = {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts p LEFT JOIN _DBPRF_icl_translations il ON p.ID = il.element_id "
                         "WHERE il.`language_code` = '" + str(
                    self.get_select_lang()) + "'  and il.`element_type` = 'post_product' and p.post_type = 'product' AND p.post_status NOT IN ('inherit','auto-draft') AND p.ID " + compare_condition + to_str(
                    self._notice['process']['products']['id_src']),
            }
        return queries

    def total_target(self):
        prefix = self._notice['target']['config']['table_prefix']
        if self._notice['target']['config'].get('site_id'):
            prefix = to_str(prefix).replace(to_str(self._notice['target']['config'].get('site_id')) + '_', '')
        queries = {
            'products': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'product' AND post_status NOT IN ('inherit','auto-draft')",
            },
            'customers': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM " + prefix + "users u LEFT JOIN " + prefix + "usermeta um ON u.ID = um.user_id WHERE (um.meta_key = '_DBPRF_capabilities' AND um.meta_value LIKE '%customer%' OR um.meta_value LIKE '%subscriber%')",
            },
            'orders': {
                'type': 'select',
                'query': "SELECT COUNT(1) AS count FROM _DBPRF_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft')"
            },
        }
        count = self.get_connector_data(self.get_connector_url('query'), {
            'serialize': True,
            'query': json.dumps(queries)
        })
        if (not count) or (count['result'] != 'success'):
            return response_error()
        real_totals = dict()
        for key, row in count['data'].items():
            total = 0
            if key == 'taxes':
                if row and to_len(row) > 0:
                    taxes = row[0]['option_value'].splitlines()
                    total = (to_len(taxes) + 1) if taxes else 1
            else:
                total = self.list_to_count_import(row, 'count')
            real_totals[key] = total
        target_total = {}
        for key, total in real_totals.items():
            if key in ['products', 'customers', 'orders']:
                target_total[key] = total
        return response_success(target_total)

    def display_import_source(self):
        if self._notice['config']['add_new']:
            self.display_recent_data()

        queries = self.get_query_display_import_source()
        count = self.get_connector_data(self.get_connector_url('query'), {
            'serialize': True,
            'query': json.dumps(queries)
        })
        if (not count) or (count['result'] != 'success'):
            return response_error()
        real_totals = dict()
        for key, row in count['data'].items():
            total = 0
            if key == 'taxes':
                if row and to_len(row) > 0:
                    taxes = row[0]['option_value'].splitlines()
                    total = (to_len(taxes) + 1) if taxes else 1
            else:
                total = self.list_to_count_import(row, 'count')
            real_totals[key] = total
        for key, total in real_totals.items():
            self._notice['process'][key]['total'] = total
        return response_success()

    def display_update_source(self):
        queries = self.get_query_display_import_source(True)
        count = self.select_multiple_data_connector(queries, 'count')

        if (not count) or (count['result'] != 'success'):
            return response_error()
        real_totals = dict()
        for key, row in count['data'].items():
            total = 0
            if key == 'taxes':
                if row and to_len(row) > 0:
                    taxes = row[0]['option_value'].splitlines()
                    total = (to_len(taxes) + 1) if taxes else 1
            else:
                total = self.list_to_count_import(row, 'count')
            real_totals[key] = total
        for key, total in real_totals.items():
            self._notice['process'][key]['total_update'] = total
        return response_success()

    def display_import_target(self):
        return response_success()

    def prepare_import_target(self):
        parent = super().prepare_import_target()
        if parent['result'] != 'success':
            return parent
        query_active_plugins = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'active_plugins'"
        }
        active_plugins = self.get_connector_data(self.get_connector_url('query'),
                                                 {'query': json.dumps(query_active_plugins)})
        if active_plugins and active_plugins['data']:
            active_plugin = active_plugins['data'][0]
            active_plugin_v = active_plugin['option_value']
            if active_plugin_v:
                active_plugin_v_data = php_unserialize(active_plugin_v)
                if active_plugin_v_data and isinstance(active_plugin_v_data, dict):
                    active_plugin_v_data = list(active_plugin_v_data.values())
                if active_plugin_v_data and "woocommerce-multilingual/wpml-woocommerce.php" in active_plugin_v_data:
                    self._notice['target']['support']['wpml'] = True
                    query_active_languages = {
                        'type': 'select',
                        'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'icl_sitepress_settings'"
                    }
                    options_data = self.get_connector_data(self.get_connector_url('query'),
                                                           {'query': json.dumps(query_active_languages)})
                    if options_data and options_data['data']:
                        option_value = php_unserialize(options_data['data'][0]['option_value'])
                        if option_value and 'default_language' in option_value:
                            self._notice['target']['language_default'] = option_value['default_language']
                woo_brands = [
                    {'name': 'woocommerce-brand/main.php'},
                    {'name': 'wc-brand/woocommerce-brand.php'},
                    {'name': 'woocommerce-brands/woocommerce-brands.php'},
                    {'name': 'brands-for-woocommerce/woocommerce-brand.php', 'taxonomy': 'berocket_brand'},
                    {'name': 'perfect-woocommerce-brands/main.php', 'taxonomy': 'pwb-brand'},
                ]
                for brand in woo_brands:
                    if brand['name'] in active_plugin_v_data:
                        self._notice['target']['support']['plugin_manufacturers'] = False
                        if brand.get('taxonomy'):
                            self._notice['target']['config']['brand_taxonomy'] = brand['taxonomy']
                        break
                if active_plugin_v_data and ((
                                                     "woocommerce-sequential-order-numbers/woocommerce-sequential-order-numbers.php" in active_plugin_v_data) or (
                                                     "custom-order-numbers-for-woocommerce/custom-order-numbers-for-woocommerce.php" in active_plugin_v_data) or (
                                                     "sequential-order-numbers-for-woocommerce/sequential-order-numbers.php" in active_plugin_v_data)):
                    self._notice['target']['support']['plugin_pre_ord'] = True
                if active_plugin_v_data and "wordpress-seo/wp-seo.php" in active_plugin_v_data:
                    self._notice['target']['support']['yoast_seo'] = True
                if "themedelights-addons/themedelights-addons.php" in active_plugin_v_data or "woocommerce-product-addons/woocommerce-product-addons.php" in active_plugin_v_data:
                    self._notice['target']['support']['addons'] = True
                if "leurlrewrite/leurlrewrite.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_seo'] = True
                    self._notice['target']['support']['plugin_seo_301'] = True
                if "leprespass/leprespass.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_cus_pass'] = True
                if "woo-product-bundle-premium/index.php" in active_plugin_v_data:
                    self._notice['target']['support']['product_bundle'] = True
                if "woocommerce-admin/woocommerce-admin.php" in active_plugin_v_data:
                    self._notice['target']['support']['plugin_woo_admin'] = True
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            query = self.dict_to_create_table_sql(self.lecm_rewrite_table_construct())
            self.query_data_connector({'type': 'query', 'query': query['query']})
        if self._notice['target']['support']['wpml'] or self._notice['target']['support'].get('polylang'):
            add_column = "ALTER TABLE " + self.get_table_name(TABLE_MAP) + " ADD `lang` VARCHAR(255)"
            self.query_raw(add_column)
            add_column = "ALTER TABLE _DBPRF_lecm_rewrite ADD `lang` VARCHAR(255)"
            self.query_data_connector({'type': 'query', 'query': add_column})
        return response_success()

    def display_confirm_target(self):
        self._notice['target']['clear']['function'] = 'clear_target_taxes'
        self._notice['target']['clear_demo']['function'] = 'clear_target_products_demo'
        return response_success()

    # TODO clear demo
    def clear_target_manufacturers_demo(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_categories_demo',
        }
        self._notice['target']['clear_demo'] = next_clear
        if not self._notice['config']['manufacturers']:
            return next_clear
        where = {
            'migration_id': self._migration_id,
            'type': self.TYPE_MANUFACTURER
        }
        manufacturers = self.select_obj(TABLE_MAP, where)
        manufacturer_ids = list()
        if manufacturers['result'] == 'success':
            manufacturer_ids = duplicate_field_value_from_list(manufacturers['data'], 'id_desc')

        if not manufacturer_ids:
            return next_clear
        manufacturer_id_con = self.list_to_in_condition(manufacturer_ids)

        taxonomy_meta_table = 'termmeta'
        collections_query = {
            'type': 'select',
            'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_brand' OR taxonomy = 'brand' OR taxonomy = 'pwb-brand' AND term_id IN " + manufacturer_id_con
        }
        manufacturers = self.get_connector_data(self.get_connector_url('query'),
                                                {'query': json.dumps(collections_query)})
        if manufacturers['data']:
            all_queries = list()
            taxonomy_ids = duplicate_field_value_from_list(manufacturers['data'], 'term_taxonomy_id')
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_" + taxonomy_meta_table + "` WHERE term_id IN " + manufacturer_id_con
            })
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + manufacturer_id_con
            })
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
                    taxonomy_ids)
            })
            if all_queries:
                self.import_multiple_data_connector(all_queries, 'cleardemo')
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
        category_id_con = self.list_to_in_condition(category_ids)
        taxonomy_meta_table = 'termmeta'

        collections_query = {
            'type': 'select',
            'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_cat' OR taxonomy = 'post_cat' AND term_id IN " + category_id_con
        }
        categories = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(collections_query)})
        if categories['data']:
            all_queries = list()
            taxonomy_ids = duplicate_field_value_from_list(categories['data'], 'term_taxonomy_id')
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_" + taxonomy_meta_table + "` WHERE term_id IN " + category_id_con
            })
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + category_id_con
            })
            all_queries.append({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
                    taxonomy_ids)
            })
            if self._notice['target']['support']['wpml']:
                clear_table = self.get_connector_data(self.get_connector_url('query'), {
                    'query': json.dumps({
                        'type': 'query',
                        'query': "DELETE FROM `_DBPRF_icl_translations` "
                                 "WHERE element_type = 'tax_product_cat' AND element_id IN " + category_id_con
                    })
                })
            if self._notice['config']['seo'] or self._notice['config']['seo_301']:
                clear_table = self.get_connector_data(self.get_connector_url('query'), {
                    'query': json.dumps({
                        'type': 'query',
                        'query': "DELETE FROM `_DBPRF_lecm_rewrite` where type = 'category' and type_id IN " + category_id_con
                    })
                })
            if all_queries:
                self.import_multiple_data_connector(all_queries, 'cleardemo')
        return next_clear

    def clear_target_products_demo(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_orders_demo',
        }
        if not self._notice['config']['products']:
            self._notice['target']['clear_demo'] = next_clear
            return next_clear
        where = {
            'migration_id': self._migration_id,
            'type': self.TYPE_PRODUCT
        }
        products = self.select_page(TABLE_MAP, where, self.LIMIT_CLEAR_DEMO)
        product_ids = list()
        if products['result'] == 'success':
            product_ids = duplicate_field_value_from_list(products['data'], 'id_desc')
        if not product_ids:
            self._notice['target']['clear_demo'] = next_clear
            return next_clear
        product_id_con = self.list_to_in_condition(product_ids)
        collections_query = {
            'type': 'select',
            'query': "SELECT * FROM `_DBPRF_posts` "
                     "WHERE ID IN " + product_id_con + " OR post_parent IN " + product_id_con
        }
        products = self.get_connector_data(self.get_connector_url('query'),
                                           {'query': json.dumps(collections_query)})
        all_post_id = list()
        if products['data']:
            all_post_id = duplicate_field_value_from_list(products['data'], 'ID')
        all_collections_query = {
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_posts` "
                     "WHERE ID IN " + self.list_to_in_condition(all_post_id)
        }
        clear_table = self.get_connector_data(self.get_connector_url('query'),
                                              {'query': json.dumps(all_collections_query)})
        all_meta_query = {
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_post_meta`"
                     " WHERE post_id IN " + self.list_to_in_condition(all_post_id)
        }
        clear_table = self.get_connector_data(self.get_connector_url('query'),
                                              {'query': json.dumps(all_meta_query)})
        where = {
            'migration_id': self._migration_id,
            'type': self.TYPE_OPTION
        }
        attibutes = self.select_obj(TABLE_MAP, where)
        attibutes_ids = list()
        attibutes_codes = list()
        if attibutes['result'] == 'success':
            attibutes_ids = duplicate_field_value_from_list(attibutes['data'], 'id_desc')
            attibutes_codes = duplicate_field_value_from_list(attibutes['data'], 'value')
        if attibutes_ids:
            del_transient_attr_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_woocommerce_attribute_taxonomies` WHERE attribute_id IN " + self.list_to_in_condition(
                    attibutes_ids)
            }
            self.get_connector_data(self.get_connector_url('query'),
                                    {'query': json.dumps(del_transient_attr_query)})
            term_query = {
                "type": "select",
                "query": "SELECT * FROM `_DBPRF_term_taxonomy` tt LEFT JOIN `_DBPRF_terms` t ON tt.term_id = t.term_id "
                         "WHERE tt.taxonomy IN " + self.list_to_in_condition(attibutes_codes)
            }
            terms = self.get_connector_data(self.get_connector_url('query'),
                                            {'query': json.dumps(term_query)})
            if (terms['data']):
                term_ids = duplicate_field_value_from_list(terms['data'], 'term_id')
                taxonomy_ids = duplicate_field_value_from_list(terms['data'], 'term_taxonomy_id')
                del_transient_attr_query = {
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
                        taxonomy_ids)
                }
                self.get_connector_data(self.get_connector_url('query'),
                                        {'query': json.dumps(del_transient_attr_query)})
                del_transient_attr_query = {
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + self.list_to_in_condition(
                        term_ids)
                }
                self.get_connector_data(self.get_connector_url('query'),
                                        {'query': json.dumps(del_transient_attr_query)})

        if self._notice['target']['support']['wpml']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_icl_translations` "
                             "WHERE element_type = 'post_product' AND element_id IN " + product_id_con
                })
            })
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_lecm_rewrite` where type = 'product' and type_id IN " + product_id_con
                })
            })
        self.delete_map_demo(self.TYPE_PRODUCT, product_ids)
        if product_ids and to_len(product_ids) < self.LIMIT_CLEAR_DEMO:
            self._notice['target']['clear_demo'] = next_clear
            return next_clear
        return self._notice['target']['clear_demo']

    def clear_target_customers_demo(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_orders_demo',
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
        customer_id_con = self.list_to_in_condition(customer_ids)
        del_user_query = "DELETE FROM _DBPRF_users WHERE ID IN " + customer_id_con
        clear_table = self.get_connector_data(self.get_connector_url('query'), {
            'query': json.dumps({
                'type': 'query', 'query': del_user_query
            })
        })
        if (not clear_table) or (clear_table['result'] != 'success') or (not clear_table['data']):
            self.log("Clear data failed. Error: Could not empty customers ", 'clear')
        del_user_meta_query = "DELETE FROM _DBPRF_usermeta WHERE user_id IN " + customer_id_con
        clear_table = self.get_connector_data(self.get_connector_url('query'), {
            'query': json.dumps({
                'type': 'query', 'query': del_user_meta_query
            })
        })

        if self._notice['target']['support'].get('plugin_woo_admin') or self.convert_version(
                self._notice['target']['config']['version'], 2) > 399:
            del_customer_lookup_query = "DELETE FROM _DBPRF_wc_customer_lookup WHERE user_id IN " + customer_id_con
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query', 'query': del_customer_lookup_query
                })
            })

        return next_clear

    def clear_target_orders_demo(self):
        next_clear = {
            'result': 'success',
            'function': 'clear_target_reviews_demo',
        }
        if not self._notice['config']['orders']:
            self._notice['target']['clear_demo'] = next_clear

            return next_clear
        where = {
            'migration_id': self._migration_id,
            'type': self.TYPE_ORDER
        }
        orders = self.select_page(TABLE_MAP, where, self.LIMIT_CLEAR_DEMO)

        order_ids = list()
        if orders['result'] == 'success':
            order_ids = duplicate_field_value_from_list(orders['data'], 'id_desc')
        if not order_ids:
            self._notice['target']['clear_demo'] = next_clear
            return next_clear
        all_collections_query = {
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_posts` WHERE post_type IN ('shop_order', 'shop_order_refund') AND ID IN " + self.list_to_in_condition(
                order_ids)
        }
        clear_table = self.get_connector_data(self.get_connector_url('query'),
                                              {'query': json.dumps(all_collections_query)})

        # clear meta post(orders)
        all_meta_query = {
            'type': 'select',
            'query': "DELETE FROM `_DBPRF_post_meta` WHERE post_id IN " + self.list_to_in_condition(order_ids)
        }
        clear_table = self.get_connector_data(self.get_connector_url('query'),
                                              {'query': json.dumps(all_meta_query)})
        self.delete_map_demo(self.TYPE_ORDER, order_ids)
        if order_ids and to_len(order_ids) < self.LIMIT_CLEAR_DEMO:
            self._notice['target']['clear_demo'] = next_clear
            return next_clear
        return self._notice['target']['clear_demo']

    def clear_target_reviews_demo(self):
        next_clear = {
            'result': 'success',
            'function': 'clear_target_pages_demo',
        }
        self._notice['target']['clear_demo'] = next_clear
        if not self._notice['config']['reviews']:
            return next_clear
        where = {
            'migration_id': self._migration_id,
            'type': self.TYPE_REVIEW
        }
        reviews = self.select_obj(TABLE_MAP, where)
        review_ids = list()
        if reviews['result'] == 'success':
            review_ids = duplicate_field_value_from_list(reviews['data'], 'id_desc')
        if not review_ids:
            return next_clear
        tables = [
            'commentmeta',
            'comments'
        ]
        for table in tables:
            where = ''
            if table == 'comments':
                where = " WHERE comment_ID IN " + self.list_to_in_condition(review_ids)
            if table == 'commentmeta':
                where = " WHERE comment_id IN " + self.list_to_in_condition(review_ids)

            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query', 'query': "DELETE FROM `_DBPRF_" + table + "`" + where
                })
            })
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
                continue

    # TODO: clear
    def clear_target_taxes(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_manufacturers',
            'msg': ''
        }
        if not self._notice['config']['taxes']:
            self._notice['target']['clear'] = next_clear
            return next_clear
        tables = [
            'options',
            'woocommerce_tax_rates',
            'woocommerce_tax_rate_locations',
            'wc_tax_rate_classes'
        ]
        for table in tables:
            if table == 'options':
                clear_table = self.get_connector_data(self.get_connector_url('query'), {
                    'query': json.dumps({
                        'type': 'query',
                        'query': "UPDATE `_DBPRF_" + table + "` SET `option_value` = '' WHERE `option_name` = 'woocommerce_tax_classes'"
                    })
                })
                continue
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_" + table + "` WHERE 1"
                })
            })
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
                continue
        self._notice['target']['clear'] = next_clear
        return next_clear

    def clear_target_manufacturers(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_categories',
            'msg': ''
        }
        if not self._notice['config']['manufacturers']:
            self._notice['target']['clear'] = next_clear
            return next_clear

        taxonomy_meta_table = 'termmeta'
        taxonomy = 'berocket_brand'
        if self._notice['target']['config'].get('brand_taxonomy'):
            taxonomy = self._notice['target']['config']['brand_taxonomy']
        # all_collections_query = {
        # 	'type': 'select',
        # 	'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_brand' OR taxonomy = 'brand' OR taxonomy = 'pwb-brand'  LIMIT 200"
        # }
        # manufacturers = self.get_connector_data(self.get_connector_url('query'),
        #                                         {'query': json.dumps(all_collections_query)})
        tables = ['termmeta', 'terms', 'term_relationships', 'term_taxonomy']
        for table in tables:
            where = ''
            if table in ['termmeta', 'terms']:
                where = " term_id IN (SELECT term_id FROM `_DBPRF_term_taxonomy` WHERE taxonomy = " + self.escape(
                    taxonomy) + " )"
            if table in ['term_relationships']:
                where = " term_taxonomy_id IN (SELECT term_taxonomy_id FROM `_DBPRF_term_taxonomy` WHERE taxonomy = " + self.escape(
                    taxonomy) + " )"
            if table == 'term_taxonomy':
                where = " taxonomy = " + self.escape(taxonomy)
            query = "DELETE FROM `_DBPRF_" + table + "` WHERE " + where
            clear_table = self.query_data_connector({'type': 'delete', 'query': query})
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
                continue
        # if manufacturers:
        # 	while manufacturers['data']:
        # 		if not manufacturers:
        # 			return next_clear
        # 		term_ids = duplicate_field_value_from_list(manufacturers['data'], 'term_id')
        # 		all_queries = list()
        # 		taxonomy_ids = duplicate_field_value_from_list(manufacturers['data'], 'term_taxonomy_id')
        # 		all_queries.append({
        # 			'type': 'query',
        # 			'query': "DELETE FROM `_DBPRF_" + taxonomy_meta_table + "` WHERE term_id IN " + self.list_to_in_condition(
        # 				term_ids)
        # 		})
        # 		all_queries.append({
        # 			'type': 'query',
        # 			'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + self.list_to_in_condition(
        # 				term_ids)
        # 		})
        # 		all_queries.append({
        # 			'type': 'query',
        # 			'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
        # 				taxonomy_ids)
        # 		})
        # 		if all_queries:
        # 			self.import_multiple_data_connector(all_queries, 'cleardemo')
        # 		all_collections_query = {
        # 			'type': 'select',
        # 			'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_brand' OR taxonomy = 'brand' OR taxonomy = 'pwb-brand' LIMIT 200"
        # 		}
        # 		manufacturers = self.get_connector_data(self.get_connector_url('query'),
        # 		                                        {'query': json.dumps(all_collections_query)})
        if self._notice['target']['support']['yoast_seo']:
            query_wpseo = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'wpseo_taxonomy_meta'"
            }
            options_data = self.get_connector_data(self.get_connector_url('query'),
                                                   {'query': json.dumps(query_wpseo)})
            if options_data and options_data['data']:
                option_value = php_unserialize(options_data['data'][0]['option_value'])
                if taxonomy in option_value:
                    option_value[taxonomy] = dict()
                data_set = {
                    'option_value': php_serialize(option_value)
                }
                where = {
                    'option_id': options_data['data'][0]['option_id'],
                    'option_name': 'wpseo_taxonomy_meta'
                }
                update_query = self.create_update_query_connector('options', data_set, where)
                wpseo_taxonomy_clear = self.import_data_connector(update_query, 'manufacturer')
        self._notice['target']['clear'] = next_clear
        return next_clear

    def clear_target_categories(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_products',
            'msg': ''
        }
        if not self._notice['config']['categories']:
            self._notice['target']['clear'] = next_clear
            return next_clear
        taxonomy_meta_table = 'termmeta'
        while self._check_categories_exists():
            all_collections_query = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_cat' OR taxonomy = 'post_cat' LIMIT 200"
            }
            categories = self.get_connector_data(self.get_connector_url('query'),
                                                 {'query': json.dumps(all_collections_query)})
            if not categories:
                return next_clear
            term_ids = duplicate_field_value_from_list(categories['data'], 'term_id')

            taxonomy_ids = duplicate_field_value_from_list(categories['data'], 'term_taxonomy_id')
            taxnomy_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_" + taxonomy_meta_table + "` WHERE term_id IN " + self.list_to_in_condition(
                    term_ids)
            }
            self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(taxnomy_query)})
            self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + self.list_to_in_condition(
                    term_ids)
            })})

            self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps({
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
                    taxonomy_ids)
            })
            })
        # end for
        if self._notice['target']['support']['wpml']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_icl_translations` where element_type = 'tax_product_cat'"
                })
            })
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_lecm_rewrite` where type = 'category'"
                })
            })
        if self._notice['target']['support']['yoast_seo']:
            query_wpseo = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'wpseo_taxonomy_meta'"
            }
            options_data = self.get_connector_data(self.get_connector_url('query'),
                                                   {'query': json.dumps(query_wpseo)})
            if options_data and options_data['data']:
                option_value = php_unserialize(options_data['data'][0]['option_value'])
                if 'product_cat' in option_value:
                    option_value['product_cat'] = dict()
                data_set = {
                    'option_value': php_serialize(option_value)
                }
                where = {
                    'option_id': options_data['data'][0]['option_id'],
                    'option_name': 'wpseo_taxonomy_meta'
                }
                update_query = self.create_update_query_connector('options', data_set, where)
                wpseo_taxonomy_clear = self.import_data_connector(update_query, 'category')
        self._notice['target']['clear'] = next_clear
        return self._notice['target']['clear']

    def _check_categories_exists(self):
        all_collections_query = {
            'type': 'select',
            'query': "SELECT term_taxonomy_id FROM `_DBPRF_term_taxonomy` WHERE taxonomy = 'product_cat' OR taxonomy = 'post_cat' LIMIT 1"
        }
        categories = self.get_connector_data(self.get_connector_url('query'),
                                             {'query': json.dumps(all_collections_query)})
        return True if categories['data'] else False

    def _check_product_exists(self):
        all_collections_query = {
            'type': 'select',
            'query': "SELECT ID FROM `_DBPRF_posts` WHERE post_type  IN ('product', 'product_variation') LIMIT 1"
        }
        # products = self.get_connector_data(self.get_connector_url('query'),
        #                                    {'query': json.dumps(all_collections_query)})
        products = self.select_data_connector(all_collections_query, 'products')
        return True if products['data'] else False

    def _check_attributes_exists(self):
        all_collections_query = {
            'type': 'select',
            'query': "SELECT * FROM `_DBPRF_woocommerce_attribute_taxonomies` ORDER BY attribute_id LIMIT 200"
        }
        products = self.get_connector_data(self.get_connector_url('query'),
                                           {'query': json.dumps(all_collections_query)})

        return True if products['data'] else False

    def clear_target_products(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_customers',
            'msg': ''
        }
        if not self._notice['config']['products']:
            self._notice['target']['clear'] = next_clear
            return next_clear

        while self._check_product_exists():
            # clear posts(product)
            # clear meta post(product)
            all_collections_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_posts` WHERE post_type IN('product', 'product_variation')"
            }
            clear_table = self.get_connector_data(self.get_connector_url('query'),
                                                  {'query': json.dumps(all_collections_query)})
            if (not clear_table) or (clear_table['result'] != 'success') or (not clear_table['data']):
                self.log("Clear data failed. Error: Could not empty products", 'clear')
                continue
            all_meta_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_postmeta` WHERE post_id NOT IN (SELECT ID FROM _DBPRF_posts)"
            }
            clear_table = self.get_connector_data(self.get_connector_url('query'),
                                                  {'query': json.dumps(all_meta_query)})

            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty products", 'clear')
                continue
        # clear attributes
        del_transient_attr_query = {
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE option_name = '_transient_wc_attribute_taxonomies'"
        }
        clear_table = self.get_connector_data(self.get_connector_url('query'),
                                              {'query': json.dumps(del_transient_attr_query)})
        while self._check_attributes_exists():
            product_attribute_query = {
                "type": "select",
                "query": "SELECT * FROM `_DBPRF_woocommerce_attribute_taxonomies` ORDER BY attribute_id LIMIT 200"
            }
            attributes = self.get_connector_data(self.get_connector_url('query'),
                                                 {'query': json.dumps(product_attribute_query)})
            if (attributes['data']):
                attribute_ids = duplicate_field_value_from_list(attributes['data'], 'attribute_id')
                attribute_names = duplicate_field_value_from_list(attributes['data'], 'attribute_name')
                attribute_names_condition = "('pa_" + "','pa_".join(attribute_names) + "')"
                del_transient_attr_query = {
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_woocommerce_attribute_taxonomies` WHERE attribute_id IN " + self.list_to_in_condition(
                        attribute_ids)
                }
                self.get_connector_data(self.get_connector_url('query'),
                                        {'query': json.dumps(del_transient_attr_query)})
                term_query = {
                    "type": "select",
                    "query": "SELECT * FROM `_DBPRF_term_taxonomy` tt LEFT JOIN `_DBPRF_terms` t ON tt.term_id = t.term_id "
                             "WHERE tt.taxonomy IN " + attribute_names_condition
                }
                terms = self.get_connector_data(self.get_connector_url('query'),
                                                {'query': json.dumps(term_query)})
                if (terms['data']):
                    term_ids = duplicate_field_value_from_list(terms['data'], 'term_id')
                    taxonomy_ids = duplicate_field_value_from_list(terms['data'], 'term_taxonomy_id')
                    del_transient_attr_query = {
                        'type': 'query',
                        'query': "DELETE FROM `_DBPRF_term_taxonomy` WHERE term_taxonomy_id IN " + self.list_to_in_condition(
                            taxonomy_ids)
                    }
                    self.get_connector_data(self.get_connector_url('query'),
                                            {'query': json.dumps(del_transient_attr_query)})
                    del_transient_attr_query = {
                        'type': 'query',
                        'query': "DELETE FROM `_DBPRF_terms` WHERE term_id IN " + self.list_to_in_condition(
                            term_ids)
                    }
                    self.get_connector_data(self.get_connector_url('query'),
                                            {'query': json.dumps(del_transient_attr_query)})

        if self._notice['target']['support']['wpml']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_icl_translations` where element_type LIKE 'tax_pa_%' OR element_type IN ('post_product','post_product_variation')"
                })
            })
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query',
                    'query': "DELETE FROM `_DBPRF_lecm_rewrite` where type = 'product'"
                })
            })
        self._notice['target']['clear'] = next_clear
        return self._notice['target']['clear']

    def clear_target_customers(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_orders',
            'msg': ''
        }
        if not self._notice['config']['customers']:
            self._notice['target']['clear'] = next_clear
            return next_clear
        # "DELETE FROM `wp_usermeta`
        # WHERE meta_key IN ('wp_capabilities', 'wp_capabilities') AND meta_value = 'a:1:{s:8:"customer";b:1;}'"
        del_user_query = "DELETE _DBPRFT_users FROM _DBPRFT_users " \
                         "LEFT JOIN _DBPRFT_usermeta ON _DBPRFT_users.ID = _DBPRFT_usermeta.user_id " \
                         "WHERE _DBPRFT_usermeta.meta_key IN ('_DBPRF_capabilities', '_DBPRF_capabilities') " \
                         "AND _DBPRFT_usermeta.meta_value IN ('a:1:{s:8:\"customer\";b:1;}')"
        prefix = to_str(self._notice['target']['config']['table_prefix'])
        if self._notice['target']['config'].get('site_id'):
            prefix = to_str(prefix)[::-1].replace('_' + to_str(self._notice['target']['config'].get('site_id')), '', 1)[
                     ::-1]
        del_user_query = del_user_query.replace('_DBPRFT_', prefix)
        self.log(del_user_query, 'del_user_query')
        clear_table = self.get_connector_data(self.get_connector_url('query'), {
            'query': json.dumps({
                'type': 'query', 'query': del_user_query
            })
        })
        if (not clear_table) or (clear_table['result'] != 'success') or (not clear_table['data']):
            self.log("Clear data failed. Error: Could not empty customers ", 'clear')
        del_user_meta_query = "DELETE _DBPRF_usermeta  FROM _DBPRF_usermeta " \
                              "LEFT JOIN _DBPRF_users ON _DBPRF_usermeta.user_id = _DBPRF_users.ID WHERE _DBPRF_users.ID IS NULL"
        clear_table = self.get_connector_data(self.get_connector_url('query'), {
            'query': json.dumps({
                'type': 'query', 'query': del_user_meta_query
            })
        })

        if self._notice['target']['support'].get('plugin_woo_admin') or self.convert_version(
                self._notice['target']['config']['version'], 2) > 399:
            del_customer_lookup_query = "DELETE _DBPRF_wc_customer_lookup  FROM _DBPRF_wc_customer_lookup LEFT JOIN _DBPRF_users ON _DBPRF_wc_customer_lookup.user_id = _DBPRF_users.ID WHERE _DBPRF_users.ID IS NULL"
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query', 'query': del_customer_lookup_query
                })
            })

        self._notice['target']['clear'] = next_clear
        return self._notice['target']['clear']

    def _check_order_exists(self):
        all_collections_query = {
            'type': 'select',
            'query': "SELECT ID FROM `_DBPRF_posts` WHERE post_type  IN ('shop_order', 'shop_order_refund') LIMIT 1"
        }
        products = self.get_connector_data(self.get_connector_url('query'),
                                           {'query': json.dumps(all_collections_query)})

        return True if products['data'] else False

    def clear_target_orders(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_reviews',
            'msg': ''
        }
        if not self._notice['config']['orders']:
            self._notice['target']['clear'] = next_clear
            return next_clear
        while self._check_order_exists():
            # clear posts(orders)
            all_collections_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_posts` WHERE post_type IN ('shop_order', 'shop_order_refund')"
            }
            clear_table = self.get_connector_data(self.get_connector_url('query'),
                                                  {'query': json.dumps(all_collections_query)})
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty products", 'clear')
                continue
            # clear meta post(orders)
            all_meta_query = {
                'type': 'select',
                'query': "DELETE `_DBPRF_postmeta` FROM `_DBPRF_post_meta` pm LEFT JOIN `_DBPRF_posts` p ON p.ID = pm.meta_id"
                         " WHERE p.ID IS NULL"
            }
            clear_table = self.get_connector_data(self.get_connector_url('query'),
                                                  {'query': json.dumps(all_meta_query)})

            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty products", 'clear')
                continue
        self._notice['target']['clear'] = next_clear
        return self._notice['target']['clear']

    def clear_target_reviews(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_blogs',
            'msg': ''
        }
        if not self._notice['config']['reviews']:
            self._notice['target']['clear'] = next_clear
            return next_clear
        tables = [
            'commentmeta',
            'comments'
        ]
        for table in tables:
            self._notice['target']['clear']['result'] = 'process'
            self._notice['target']['clear']['function'] = 'clear_target_reviews'
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query', 'query': "DELETE FROM `_DBPRF_" + table + "`"
                })
            })
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
                continue
        self._notice['target']['clear'] = next_clear
        return self._notice['target']['clear']

    # def clear_target_blogs(self):
    # 	next_clear = {
    # 		'result': 'process',
    # 		'function': 'clear_target_coupons',
    # 		'msg': ''
    # 	}
    # 	self._notice['target']['clear'] = next_clear
    # 	if not self._notice['config'].get('blogs'):
    # 		return next_clear
    # 	all_queries = {
    # 		'term': {
    # 			'type': 'delete',
    # 			'query': 'DELETE FROM _DBPRF_terms WHERE term_id IN (SELECT term_id FROM _DBPRF_term_taxonomy WHERE taxonomy IN ' + self.list_to_in_condition(['category', 'post_tag']) + ')'
    # 		},
    # 		'term_taxonomy': {
    # 			'type': 'delete',
    # 			'query': 'DELETE FROM _DBPRF_term_taxonomy WHERE taxonomy IN ' + self.list_to_in_condition(['category', 'post_tag'])
    # 		},
    # 		'term_relationship': {
    # 			'type': 'delete',
    # 			'query': 'DELETE FROM _DBPRF_term_relationships WHERE object_id IN (SELECT ID FROM _DBPRF_posts WHERE post_type = "post")'
    # 		},
    # 		'postmeta': {
    # 			'type': 'delete',
    # 			'query': 'DELETE FROM _DBPRF_postmeta WHERE post_id IN (SELECT ID FROM _DBPRF_posts WHERE post_type = "post")'
    # 		},
    # 		'posts': {
    # 			'type': 'delete',
    # 			'query': 'DELETE FROM _DBPRF_posts WHERE post_type = "post"'
    # 		},
    # 	}
    # 	delete = self.query_multiple_data_connector(all_queries, 'clear_blog')
    # 	return next_clear

    def clear_target_coupons(self):
        next_clear = {
            'result': 'process',
            'function': 'clear_target_pages',
            'msg': ''
        }
        self._notice['target']['clear'] = next_clear
        if not self._notice['config']['coupons']:
            return next_clear
        tables = [
            'postmeta',
            'posts'
        ]
        for table in tables:
            where = ' post_type = "shop_coupon"'
            if table == 'postmeta':
                where = ' post_id IN (SELECT ID FROM _DBPRF_posts WHERE post_type = "shop_coupon")'
            clear_table = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'query', 'query': "DELETE FROM `_DBPRF_" + table + "` WHERE " + where
                })
            })
            if (not clear_table) or (clear_table['result'] != 'success'):
                self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
                continue
        return next_clear

    # def clear_target_pages(self):
    # 	next_clear = {
    # 		'result': 'process',
    # 		'function': '',
    # 		'msg': ''
    # 	}
    # 	self._notice['target']['clear'] = next_clear
    # 	if not self._notice['config']['pages']:
    # 		return next_clear
    # 	tables = [
    # 		'postmeta',
    # 		'posts'
    # 	]
    # 	for table in tables:
    # 		where = ' post_type = "page"'
    # 		if table == 'postmeta':
    # 			where = ' post_id IN (SELECT ID FROM _DBPRF_posts WHERE post_type = "page")'
    # 		clear_table = self.get_connector_data(self.get_connector_url('query'), {
    # 			'query': json.dumps({
    # 				'type': 'query', 'query': "DELETE FROM `_DBPRF_" + table + "` WHERE " + where
    # 			})
    # 		})
    # 		if (not clear_table) or (clear_table['result'] != 'success'):
    # 			self.log("Clear data failed. Error: Could not empty table " + table, 'clear')
    # 			continue
    # 	return next_clear

    # TODO: TAX
    def prepare_taxes_import(self):
        return self

    def prepare_taxes_export(self):
        return self

    def get_taxes_main_export(self):
        id_src = self._notice['process']['taxes']['id_src']
        limit = self._notice['setting']['taxes']
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'woocommerce_tax_classes'"
        }
        # taxes = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        taxes = self.select_data_connector(query, 'taxes')
        if not taxes or taxes['result'] != 'success':
            return response_error('could not get taxes main to export')
        list_taxes = response_success()

        if taxes['data'] and to_len(taxes['data']) > 0:
            list_taxes['data'] = list()
            for tax in taxes['data']:
                _taxes = tax['option_value'].splitlines()
                if _taxes:
                    tmp_taxes = [
                        {
                            'id': 1,
                            'name': 'Standard'
                        }
                    ]
                    i = 2
                    for tax_name in _taxes:
                        tax_data = dict()
                        tax_data['id'] = i
                        tax_data['name'] = tax_name
                        tmp_taxes.append(tax_data)
                        i += 1
                    list_taxes['data'].extend(tmp_taxes)
        return list_taxes

    def get_taxes_ext_export(self, taxes):
        url_query = self.get_connector_url('query')
        tax_product_class_names = duplicate_field_value_from_list(taxes['data'], 'name')
        tax_names = list()
        for class_name in tax_product_class_names:
            _class_name = to_str(class_name).lower()
            _class_name = _class_name.replace(' ', '-')
            tax_names.append(_class_name)
        taxes_ext_queries = {
            'tax_rates': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_tax_rates WHERE 1"
                # tax_rate_class IN " + self.list_to_in_condition(tax_names),
            }
        }
        # taxes_ext = self.get_connector_data(url_query, {'serialize': True, 'query': json.dumps(taxes_ext_queries)})
        taxes_ext = self.select_multiple_data_connector(taxes_ext_queries, 'taxes')
        if not taxes_ext or taxes_ext['result'] != 'success':
            return response_error()
        tax_zone_ids = duplicate_field_value_from_list(taxes_ext['data']['tax_rates'], 'tax_rate_id')
        taxes_ext_rel_queries = {
            'tax_rates_location': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_tax_rate_locations WHERE tax_rate_id IN " + self.list_to_in_condition(
                    tax_zone_ids),
            }
        }
        # taxes_ext_rel = self.get_connector_data(url_query,
        #                                 {'serialize': True, 'query': json.dumps(taxes_ext_rel_queries)})
        taxes_ext_rel = self.select_multiple_data_connector(taxes_ext_rel_queries, 'taxes')
        if not taxes_ext_rel or taxes_ext_rel['result'] != 'success':
            return response_error()
        taxes_ext = self.sync_connector_object(taxes_ext, taxes_ext_rel)
        return taxes_ext

    def convert_tax_export(self, tax, taxes_ext):
        tax_zones = list()
        tax_rate_class_1 = to_str(tax['name']).lower()
        tax_rate_class_1 = tax_rate_class_1.replace(' ', '-')
        if tax['name'] == 'Standard':
            tax_rate_class_1 = ''
        src_tax_rate = get_list_from_list_by_field(taxes_ext['data']['tax_rates'], 'tax_rate_class', tax_rate_class_1)
        if src_tax_rate and to_len(src_tax_rate) > 0:
            for tax_rate in src_tax_rate:
                tax_zone = self.construct_tax_zone()
                # tax_zone = self.addConstructDefault(tax_zone)
                tax_zone['id'] = tax_rate['tax_rate_id']
                tax_zone['name'] = tax_rate['tax_rate_name']
                tax_zone_country = self.construct_tax_zone_country()
                tax_zone_country['name'] = self.get_country_name_by_code(tax_rate['tax_rate_country']) if tax_rate[
                    'tax_rate_country'] else ''
                tax_zone_country['code'] = get_value_by_key_in_dict(tax_rate, 'tax_rate_country', '')
                tax_zone_country['country_code'] = get_value_by_key_in_dict(tax_rate, 'tax_rate_country', '')
                tax_zone['country'] = tax_zone_country
                tax_zone_state = self.construct_tax_zone_state()
                tax_zone_state['name'] = ''
                tax_zone_state['code'] = get_value_by_key_in_dict(tax_rate, 'tax_rate_state', '')
                tax_zone_state['state_code'] = get_value_by_key_in_dict(tax_rate, 'tax_rate_state', '')
                tax_zone['state'] = tax_zone_state
                tax_zone['rate'] = self.construct_tax_zone_rate()
                tax_zone['rate']['id'] = tax_rate['tax_rate_id']
                tax_zone['rate']['name'] = tax_rate['tax_rate_name']
                tax_zone['rate']['code'] = tax_rate['tax_rate_class']
                tax_zone['rate']['rate'] = tax_rate['tax_rate']
                tax_rates_locations = get_list_from_list_by_field(taxes_ext['data']['tax_rates_location'],
                                                                  'tax_rate_id', tax_rate['tax_rate_id'])
                tax_zone_city = get_list_from_list_by_field(tax_rates_locations, 'location_type', 'city')
                tax_zone['postcode'] = get_row_value_from_list_by_field(tax_rates_locations, 'location_type',
                                                                        'postcode', 'location_code')
                tax_zone['city'] = ''
                if tax_zone_city:
                    for _tax_zone_city in tax_zone_city:
                        tax_zone['city'] += _tax_zone_city['location_code'] + ';'
                tax_zone['priority'] = tax_rate['tax_rate_priority']
                tax_zone['compound'] = True if tax_rate['tax_rate_compound'] and to_int(
                    tax_rate['tax_rate_compound']) == 1 else False
                tax_zone['is_shipping'] = True if tax_rate['tax_rate_shipping'] and to_int(
                    tax_rate['tax_rate_shipping']) == 1 else False
                tax_zones.append(tax_zone)

        tax_product = self.construct_tax_product()
        tax_product = self.add_construct_default(tax_product)
        tax_code = to_str(tax['name']).lower()
        tax_code = tax_code.replace(' ', '-')
        tax_product['name'] = tax['name']
        tax_product['code'] = tax_code
        tax_product['created_at'] = get_current_time()
        tax_product['updated_at'] = get_current_time()
        tax_products = [tax_product]
        tax_data = self.construct_tax()
        tax_data = self.add_construct_default(tax_data)
        # id_src = self._notice['process']['taxes']['id_src']
        tax_data['id'] = tax['id']
        tax_data['code'] = tax_code  # tax['name']
        tax_data['name'] = tax['name']
        tax_data['created_at'] = get_current_time()
        tax_data['updated_at'] = get_current_time()
        tax_data['tax_zones'] = tax_zones
        tax_data['tax_products'] = tax_products
        return response_success(tax_data)

    def get_tax_id_import(self, convert, tax, taxes_ext):
        # id_src = self._notice['process']['taxes']['id_src']
        return tax['id']

    def check_tax_import(self, convert, tax, taxes_ext):
        return True if self.get_map_field_by_src(self.TYPE_TAX, convert['id'], convert['code']) else False

    def router_tax_import(self, convert, tax, taxes_ext):
        return response_success('tax_import')

    def before_tax_import(self, convert, tax, taxes_ext):
        return response_success()

    def tax_import(self, convert, tax, taxes_ext):
        slug = self.sanitize_title(convert['name'])
        if convert['name'] != 'Standard':
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_options WHERE option_name = 'woocommerce_tax_classes'"
            }
            taxes = self.select_data_connector(query, 'taxes')
            if taxes and taxes['data']:
                old_tax_data = taxes['data'][0]
                new_option_value = old_tax_data['option_value'] + '\n' + convert['name'] if old_tax_data[
                    'option_value'] else convert['name']
                query_update = {
                    'type': 'query',
                    'query': "UPDATE `_DBPRF_options` SET `option_value` = '" + new_option_value + "' WHERE `option_name` = 'woocommerce_tax_classes'"
                }
                taxes = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query_update)})
            else:
                tax_data = {
                    'option_name': 'woocommerce_tax_classes',
                    'option_value': convert['name'],
                    'autoload': 'yes'
                }
                tax_query = self.create_insert_query_connector('options', tax_data)
                tax_import = self.import_tax_data_connector(tax_query, True, convert['id'])
        if self.convert_version(self._notice['target']['config']['version'], 2) >= 370:
            tax_rate_classes = {
                'name': convert['name'],
                'slug': slug
            }
            tax_rate_classes_query = self.create_insert_query_connector('wc_tax_rate_classes', tax_rate_classes)
            tax_rate_classes_import = self.import_data_connector(tax_rate_classes_query, 'wc_tax_rate_classes')

        tax_code = to_str(convert['name']).lower()
        tax_code = self.sanitize_title(tax_code.replace(' ', '-'))
        self.insert_map(self.TYPE_TAX, convert['id'], 0, convert['code'], tax_code)
        return response_success(convert['id'])

    def after_tax_import(self, tax_id, convert, tax, taxes_ext):
        if convert['tax_zones']:
            tax_code = to_str(convert['name']).lower()
            tax_code = tax_code.replace(' ', '-')
            for tax_zone in convert['tax_zones']:
                tax_rate = {
                    'tax_rate_country': tax_zone['country']['country_code'],
                    'tax_rate_state': tax_zone['state']['state_code'] if tax_zone['state']['state_code'] else '*',
                    'tax_rate': tax_zone['rate']['rate'] if tax_zone['rate']['rate'] else '*',
                    'tax_rate_name': tax_zone['rate']['name'] if tax_zone['rate']['name'] else 'Tax',
                    'tax_rate_priority': tax_zone.get('priority', 1),
                    'tax_rate_compound': 1 if tax_zone.get('compound') else 0,
                    'tax_rate_shipping': 1 if tax_zone.get('is_shipping') else 0,
                    'tax_rate_order': 0,
                    'tax_rate_class': '' if convert['name'] == 'Standard' else self.convert_attribute_code(tax_code)
                }
                tax_rate_query = self.create_insert_query_connector('woocommerce_tax_rates', tax_rate)
                tax_rate_import = self.import_data_connector(tax_rate_query, 'tax')
                if get_value_by_key_in_dict(tax_zone, 'postcode', False):
                    location_postcode = {
                        'location_code': get_value_by_key_in_dict(tax_zone, 'postcode', ''),
                        'tax_rate_id': tax_rate_import,
                        'location_type': 'postcode'
                    }
                    self.import_data_connector(
                        self.create_insert_query_connector('woocommerce_tax_rate_locations', location_postcode), 'tax')
                if get_value_by_key_in_dict(tax_zone, 'city', False):
                    tax_zone_city = tax_zone['city'].split(';')
                    if tax_zone_city:
                        for _tax_zone_city in tax_zone_city:
                            if _tax_zone_city != '' and _tax_zone_city != ' ':
                                location_city = {
                                    'location_code': get_value_by_key_in_dict(tax_zone, 'city', ''),
                                    'tax_rate_id': tax_rate_import,
                                    'location_type': 'city'
                                }
                                self.import_data_connector(
                                    self.create_insert_query_connector('woocommerce_tax_rate_locations', location_city),
                                    'tax')
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
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id"
                     " WHERE (tx.taxonomy = 'product_brand' OR tx.taxonomy = 'brand' OR tx.taxonomy = 'pwb-brand') AND tx.term_id > " +
                     to_str(id_src) + " ORDER BY tx.term_id ASC LIMIT " + to_str(limit)
        }
        # manufacturers = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        manufacturers = self.select_data_connector(query, 'manufacturers')
        if not manufacturers or manufacturers['result'] != 'success':
            return response_error('could not get manufacturers main to export')
        return manufacturers

    def get_manufacturers_ext_export(self, manufacturers):
        url_query = self.get_connector_url('query')
        category_ids = duplicate_field_value_from_list(manufacturers['data'], 'term_id')
        cart_version = self.convert_version(self._notice['src']['config']['version'], 2)
        manufacturers_ext_queries = {
            'all_category': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id WHERE tx.taxonomy = 'product_cat' AND tx.term_id > 0 "
            }
        }
        if cart_version > 223:
            manufacturers_ext_queries['woocommerce_termmeta'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_termmeta WHERE term_id IN " + self.list_to_in_condition(
                    category_ids) + " AND meta_key IN ('order', 'thumbnail_id', 'display_type', 'pwb_brand_image')"
            }
        else:
            manufacturers_ext_queries['woocommerce_termmeta'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_termmeta WHERE woocommerce_term_id IN " + self.list_to_in_condition(
                    category_ids) + " AND meta_key IN ('order', 'thumbnail_id', 'display_type', 'pwb_brand_image')"
            }
        manufacturers_ext_queries['brand_taxonomy_images'] = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_options WHERE option_name IN " + self.brand_image_in_condition(category_ids)
        }

        manufacturers_ext = self.select_multiple_data_connector(manufacturers_ext_queries, 'manufacturers')

        if not manufacturers_ext or manufacturers_ext['result'] != 'success':
            return response_warning()
        thumb_id_list = get_list_from_list_by_field(manufacturers_ext['data']['woocommerce_termmeta'], 'meta_key',
                                                    'thumbnail_id')
        if not thumb_id_list:
            thumb_id_list = get_list_from_list_by_field(manufacturers_ext['data']['woocommerce_termmeta'], 'meta_key',
                                                        'pwb_brand_image')
        thumbnail_ids = duplicate_field_value_from_list(thumb_id_list, 'meta_value')
        thumb_ids_query = self.list_to_in_condition(thumbnail_ids)
        manufacturers_ext_rel_queries = {
            'post_meta': {
                'type': 'select',
                'query': "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM _DBPRF_posts AS p "
                         "LEFT JOIN _DBPRF_postmeta AS pm ON pm.post_id = p.ID AND pm.meta_key = '_wp_attached_file' WHERE p.ID IN " + thumb_ids_query
            }
        }

        if manufacturers_ext_rel_queries:

            manufacturers_ext_rel = self.select_multiple_data_connector(manufacturers_ext_rel_queries, 'manufacturers')
            if not manufacturers_ext_rel or manufacturers_ext_rel['result'] != 'success':
                return response_error()
            manufacturers_ext = self.sync_connector_object(manufacturers_ext, manufacturers_ext_rel)

        return manufacturers_ext

    def convert_manufacturer_export(self, manufacturer, manufacturers_ext):
        manufacturer_data = self.construct_manufacturer()
        manufacturer_data = self.add_construct_default(manufacturer_data)

        manufacturer_path = manufacturer_url = img_label = ''
        cart_version = self.convert_version(self._notice['src']['config']['version'], 2)
        manufacturer_src = False
        if cart_version > 223:
            manufacturer_src = get_list_from_list_by_field(manufacturers_ext['data']['woocommerce_termmeta'], 'term_id',
                                                           manufacturer['term_id'])
        else:
            manufacturer_src = get_list_from_list_by_field(manufacturers_ext['data']['woocommerce_termmeta'],
                                                           'woocommerce_term_id', manufacturer['term_id'])

        if manufacturer_src:
            manufacturer_img_id = self.get_value_metadata(manufacturer_src, 'thumbnail_id', None)
            if not manufacturer_img_id:
                manufacturer_img_id = self.get_value_metadata(manufacturer_src, 'pwb_brand_image', None)
            if manufacturer_img_id:
                img_meta = get_list_from_list_by_field(manufacturers_ext['data']['post_meta'], 'ID',
                                                       manufacturer_img_id)
                if img_meta:
                    img_label = img_meta[0]['post_title']
                    manufacturer_path = img_meta[0]['meta_value']
                    manufacturer_url = to_str(img_meta[0]['guid']).replace(img_meta[0]['meta_value'], '')
        brand_image = get_row_value_from_list_by_field(manufacturers_ext['data']['brand_taxonomy_images'],
                                                       'option_name',
                                                       "brand_taxonomy_image" + to_str(manufacturer['term_id']),
                                                       'option_value')
        if brand_image:
            manufacturer_url = brand_image
        manufacturer_data['id'] = manufacturer['term_id']
        manufacturer_data['code'] = manufacturer['slug']
        manufacturer_data['name'] = manufacturer['name']
        manufacturer_data['description'] = manufacturer['description']
        manufacturer_data['thumb_image']['label'] = img_label
        manufacturer_data['thumb_image']['url'] = manufacturer_url
        manufacturer_data['thumb_image']['path'] = manufacturer_path
        manufacturer_data['created_at'] = get_current_time()
        manufacturer_data['updated_at'] = get_current_time()
        language_id = self._notice['src']['language_default']
        manufacturer_language_data = dict()
        manufacturer_language_data['name'] = manufacturer['name']
        manufacturer_language_data['description'] = manufacturer['description']
        manufacturer_data['languages'][language_id] = manufacturer_language_data
        manufacturer_data['manufacturer'] = manufacturer
        manufacturer_data['manufacturers_ext'] = manufacturers_ext
        return response_success(manufacturer_data)

    def get_manufacturer_id_import(self, convert, manufacturer, manufacturers_ext):
        return manufacturer['term_id']

    def check_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
        return True if self.get_map_field_by_src(self.TYPE_MANUFACTURER, convert['id']) else False

    def router_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
        return response_success('manufacturer_import')

    def before_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
        return response_success()

    def manufacturer_import(self, convert, manufacturer, manufacturers_ext):
        slug = self.sanitize_title(convert['name'])
        manufacturer_term = {
            'name': convert['name'],
            'slug': convert['code'] if convert['code'] else slug,
            'term_group': 0,
        }
        manufacturer_term_query = self.create_insert_query_connector('terms', manufacturer_term)
        term_id = self.import_data_connector(manufacturer_term_query, 'category')
        if not term_id:
            return response_warning('Manufacturer ' + to_str(convert['id']) + ' import false.')
        taxonomy = 'berocket_brand'
        if self._notice['target']['config'].get('brand_taxonomy'):
            taxonomy = self._notice['target']['config']['brand_taxonomy']
        manufacturer_taxonomy = {
            'term_id': term_id,
            'taxonomy': taxonomy,
            'description': get_value_by_key_in_dict(convert, 'description', ''),
            'parent': 0,
            'count': 0
        }
        manufacturer_taxonomy_query = self.create_insert_query_connector('term_taxonomy', manufacturer_taxonomy)
        manufacturer_taxonomy_import = self.import_manufacturer_data_connector(manufacturer_taxonomy_query, True,
                                                                               convert['id'])
        if not manufacturer_taxonomy_import:
            return response_warning('manufacturer ' + to_str(convert['id']) + ' import false.')
        self.insert_map(self.TYPE_MANUFACTURER, convert['id'], manufacturer_taxonomy_import, convert['code'])
        thumbnail_id = False
        cate_image = ''
        if convert['thumb_image']['url'] or convert['thumb_image']['path']:
            image_process = self.process_image_before_import(convert['thumb_image']['url'],
                                                             convert['thumb_image']['path'])
            config_image_path = self._notice['target']['config']['image_manufacturer'].rstrip('/') if not \
                self._notice['target']['config'].get('site_id') else self._notice['target']['config'][
                                                                         'image_manufacturer'].rstrip(
                '/') + '/sites/' + to_str(self._notice['target']['config']['site_id'])
            image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                self.make_woocommerce_image_path(image_process['path'], self.TYPE_MANUFACTURER), config_image_path))
            if image_import_path:
                cate_image = self.remove_prefix_path(image_import_path,
                                                     self._notice['target']['config']['image_category'])
                _, image_details = self.get_sizes(image_process['url'])
                thumbnail_id = self.wp_image(cate_image, image_details)
        if thumbnail_id:
            meta_insert = {
                'term_id': term_id,
                # 'meta_key': 'thumbnail_id',
                'meta_key': 'pwb_brand_image',
                'meta_value': thumbnail_id
            }
            meta_query = self.create_insert_query_connector('termmeta', meta_insert)
            self.import_data_connector(meta_query, 'manufacturer')
            meta_insert = {
                'term_id': term_id,
                # 'meta_key': 'thumbnail_id',
                'meta_key': 'thumbnail_id',
                'meta_value': thumbnail_id
            }
            meta_query = self.create_insert_query_connector('termmeta', meta_insert)
            self.import_data_connector(meta_query, 'manufacturer')
            meta_insert = {
                'term_id': term_id,
                'meta_key': 'brand_image_url',
                'meta_value': self._notice['target']['cart_url'].rstrip(
                    '/') + '/wp-content/uploads/' + cate_image.lstrip('/')
            }
            meta_query = self.create_insert_query_connector('termmeta', meta_insert)
            self.import_data_connector(meta_query, 'manufacturer')
        if self.is_wpml() or self._notice['target']['support']['yoast_seo']:
            query_wpseo = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'wpseo_taxonomy_meta'"
            }
            options_data = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query_wpseo)})
            if options_data and options_data['data']:
                option_value = php_unserialize(options_data['data'][0]['option_value'])
                if not option_value:
                    option_value = dict()
                if taxonomy not in option_value.keys():
                    option_value[taxonomy] = dict()
                option_value[taxonomy][to_int(term_id)] = {
                    'wpseo_title': get_value_by_key_in_dict(convert, 'meta_title', ''),
                    'wpseo_desc': get_value_by_key_in_dict(convert, 'meta_description', ''),
                    'wpseo_linkdex': 0,
                    'wpseo_content_score': 0
                }
                data_set = {
                    'option_value': php_serialize(option_value)
                }
                where = {
                    'option_id': options_data['data'][0]['option_id'],
                    'option_name': 'wpseo_taxonomy_meta'
                }
                self.import_data_connector(self.create_update_query_connector('options', data_set, where),
                                           'manufacturer')
            else:
                new_option_data = {
                    'option_name': 'wpseo_taxonomy_meta',
                    'option_value': php_serialize({
                        taxonomy: {
                            to_int(term_id): {
                                'wpseo_title': get_value_by_key_in_dict(convert, 'meta_title', ''),
                                'wpseo_desc': get_value_by_key_in_dict(convert, 'meta_description', ''),
                                'wpseo_linkdex': 0,
                                'wpseo_content_score': 0
                            }
                        }
                    }),
                    'autoload': 'yes'
                }
                self.import_data_connector(self.create_insert_query_connector('options', new_option_data),
                                           'manufacturer')
        return response_success(manufacturer_taxonomy_import)

    def after_manufacturer_import(self, manufacturer_id, convert, manufacturer, manufacturers_ext):
        return response_success()

    def addition_manufacturer_import(self, convert, manufacturer, manufacturers_ext):
        return response_success()

    # TODO: CATEGORY
    def prepare_categories_import(self):
        parent = super().prepare_categories_import()
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            query = self.dict_to_create_table_sql(self.lecm_rewrite_table_construct())
            self.query_data_connector({'type': 'query', 'query': query['query']})
        return self

    def prepare_categories_export(self):
        return self

    def get_categories_main_export(self):
        id_src = self._notice['process']['categories']['id_src']
        limit = self._notice['setting']['categories']
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id"
                     " WHERE tx.taxonomy = 'product_cat' AND tx.term_id > " + to_str(id_src) +
                     " AND t.term_id IS NOT NULL ORDER BY tx.term_id ASC LIMIT " + to_str(limit)
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy tt "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tt.term_id "
                         "LEFT JOIN _DBPRF_icl_translations il ON tt.term_taxonomy_id = il.element_id "
                         "WHERE il.`element_type` = 'tax_product_cat' and il.`language_code` = '" +
                         str(self.get_select_lang()) + "' and tt.taxonomy = 'product_cat' and tt.term_id > " + to_str(
                    id_src) +
                         " ORDER BY tt.term_id ASC LIMIT " + to_str(limit),

            }

        categories = self.select_data_connector(query, 'categories')
        if not categories or categories['result'] != 'success':
            return response_error('could not get manufacturers main to export')
        return categories

    def get_categories_ext_export(self, categories):
        url_query = self.get_connector_url('query')
        category_ids = duplicate_field_value_from_list(categories['data'], 'term_id')
        parent_ids = duplicate_field_value_from_list(categories['data'], 'parent')
        cart_version = self.convert_version(self._notice['src']['config']['version'], 2)
        taxonomy_type = 'product_cat' if not categories.get('is_blog') else 'category'
        categories_ext_queries = {
            'all_category': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id WHERE tx.taxonomy = '" +
                         taxonomy_type + "' AND tx.term_id > 0 "
            },
            'seo_categories': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                         "WHERE tx.taxonomy = '" + taxonomy_type + "' AND tx.term_id IN " + self.list_to_in_condition(
                    parent_ids)
            }

        }
        if cart_version > 255:
            categories_ext_queries['woocommerce_termmeta'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_termmeta WHERE term_id IN " + self.list_to_in_condition(
                    category_ids) + " AND meta_key IN ('order', 'thumbnail_id', 'display_type')"
            }
        else:
            categories_ext_queries['woocommerce_termmeta'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_termmeta WHERE woocommerce_term_id IN " + self.list_to_in_condition(
                    category_ids) + " AND meta_key IN ('order', 'thumbnail_id', 'display_type')"
            }
        # add wpml
        if self._notice['src']['support']['wpml']:
            categories_ext_queries['icl_translations'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations WHERE element_type = 'tax_product_cat' and element_id IN " + self.list_to_in_condition(
                    category_ids)
            }

        categories_ext = self.get_connector_data(url_query, {
            'serialize': True,
            'query': json.dumps(categories_ext_queries)
        })

        if not categories_ext or categories_ext['result'] != 'success':
            return response_warning()

        thumb_id_list = get_list_from_list_by_field(categories_ext['data']['woocommerce_termmeta'], 'meta_key',
                                                    'thumbnail_id')
        thumbnail_ids = duplicate_field_value_from_list(thumb_id_list, 'meta_value')
        thumb_ids_query = self.list_to_in_condition(thumbnail_ids)
        categories_ext_rel_queries = {
            'post_meta': {
                'type': 'select',
                'query': "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM _DBPRF_posts AS p "
                         "LEFT JOIN _DBPRF_postmeta AS pm ON pm.post_id = p.ID AND pm.meta_key = '_wp_attached_file' WHERE p.ID IN " + thumb_ids_query
            }
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            trids = duplicate_field_value_from_list(categories_ext['data']['icl_translations'], 'trid')
            categories_ext_rel_queries['wpml_category_lang'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations il "
                         "LEFT JOIN _DBPRF_term_taxonomy as tx ON il.element_id = tx.term_id "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                         "WHERE il.element_type = 'tax_product_cat' and il.trid IN " + self.list_to_in_condition(trids)
            }
        if categories_ext_rel_queries:
            categories_ext_rel = self.select_multiple_data_connector(categories_ext_rel_queries, 'categories')
            if not categories_ext_rel or categories_ext_rel['result'] != 'success':
                return response_error()
            categories_ext = self.sync_connector_object(categories_ext, categories_ext_rel)

        return categories_ext

    def convert_category_export(self, category, categories_ext):
        category_data = self.construct_category() if not self.blog_running else self.construct_blog_category()

        parent = self.construct_category_parent() if not self.blog_running else self.construct_blog_category()
        parent['id'] = 0
        if category['parent'] and to_int(category['parent']) > 0:
            parent_data = self.get_category_parent(category['parent'])
            if parent_data['result'] == 'success' and parent_data['data']:
                parent = parent_data['data']
        category_path = img_meta = category_url = img_label = ''
        cart_version = self.convert_version(self._notice['src']['config']['version'], 2)
        if cart_version > 255:
            category_src = get_list_from_list_by_field(categories_ext['data']['woocommerce_termmeta'], 'term_id',
                                                       category['term_id'])
        else:
            category_src = get_list_from_list_by_field(categories_ext['data']['woocommerce_termmeta'],
                                                       'woocommerce_term_id', category['term_id'])

        if category_src:
            category_img_id = self.get_value_metadata(category_src, 'thumbnail_id', 0)
            img_meta = get_list_from_list_by_field(categories_ext['data']['post_meta'], 'ID', category_img_id)
            if img_meta:
                img_label = img_meta[0]['post_title']
                category_path = to_str(img_meta[0]['meta_value'])
                category_url = to_str(img_meta[0]['guid']).replace(category_path, '')

        category_data['id'] = category['term_id']
        category_data['code'] = category['slug']
        category_data['name'] = category['name']
        category_data['description'] = category['description']
        category_data['parent'] = parent
        category_data['active'] = True
        category_data['thumb_image']['label'] = img_label
        category_data['thumb_image']['url'] = category_url
        category_data['thumb_image']['path'] = category_path
        category_data['sort_order'] = 1
        category_data['created_at'] = get_current_time()
        category_data['updated_at'] = get_current_time()
        category_data['category'] = category
        category_data['categories_ext'] = categories_ext

        # todo: woo2woo
        category_data['display_type'] = self.get_value_metadata(category_src, 'display_type', '')

        if self._notice['src']['support'][PluginSupport.wpml.name]:
            trid = get_row_value_from_list_by_field(categories_ext['data']['icl_translations'], 'element_id',
                                                    category['term_taxonomy_id'], 'trid')
            if trid:
                languages_data = get_list_from_list_by_field(categories_ext['data']['wpml_category_lang'], 'trid', trid)
                if languages_data:
                    for language_data in languages_data:
                        category_new_data = self.construct_category_lang()
                        category_new_data['id'] = language_data['term_id']
                        category_new_data['code'] = language_data['slug']
                        category_new_data['name'] = language_data['name']
                        category_new_data['description'] = language_data['description']
                        if to_int(language_data['term_id']) == to_int(category['term_id']):
                            category_data['language_default'] = language_data['language_code']
                        elif 'language_default' not in category_data and not language_data['source_language_code']:
                            category_data['language_default'] = language_data['language_code']
                        category_data['languages'][language_data['language_code']] = category_new_data
        else:
            category_language_data = self.construct_category_lang()
            language_id = self._notice['src']['language_default']
            category_language_data['name'] = category['name']
            category_language_data['description'] = category['description']
            category_data['languages'][language_id] = category_language_data
        query_wpseo = {
            'type': 'select',
            'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'wpseo_taxonomy_meta'"
        }
        options_data = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query_wpseo)})
        if options_data and options_data['data']:
            option_value = php_unserialize(options_data['data'][0]['option_value'])
            if option_value and 'product_cat' in option_value:
                if to_int(category['term_id']) in option_value['product_cat']:
                    category_data['meta_title'] = get_value_by_key_in_dict(
                        option_value['product_cat'][to_int(category['term_id'])], 'wpseo_title', '')
                    category_data['meta_description'] = get_value_by_key_in_dict(
                        option_value['product_cat'][to_int(category['term_id'])], 'wpseo_desc', '')
                    category_data['meta_keyword'] = get_value_by_key_in_dict(
                        option_value['product_cat'][to_int(category['term_id'])], 'wpseo_focuskw', '')

        detect_seo = self.detect_seo()
        category_data['seo'] = getattr(self, 'categories_' + detect_seo)(category, categories_ext)
        return response_success(category_data)

    def get_category_parent(self, parent_id):
        type_map = self.TYPE_CATEGORY if not self.blog_running else self.TYPE_CATEGORY_BLOG
        category_exist = self.select_map(self._migration_id, type_map, parent_id)
        if category_exist:
            return response_success({
                'id': parent_id,
                'code': ''
            })
        taxonomy_type = 'product_cat' if not self.blog_running else 'category'
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_term_taxonomy as tx LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                     "WHERE tx.taxonomy = '" + taxonomy_type + "' AND tx.term_id = " + to_str(parent_id)
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy tt LEFT JOIN _DBPRF_terms AS t ON t.term_id = tt.term_id "
                         "LEFT JOIN _DBPRF_icl_translations il ON tt.term_taxonomy_id = il.element_id "
                         "WHERE il.`element_type` = 'tax_product_cat' AND il.`source_language_code` IS NULL AND tt.taxonomy = '" +
                         taxonomy_type + "' and tt.term_id = " + to_str(parent_id),

            }
        categories = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        if not categories or categories['result'] != 'success':
            return response_error('could not get category parent to export')
        if categories and categories['data']:
            category = categories['data'][0]
            categories_ext = self.get_categories_ext_export(categories)
            category_convert = self.convert_category_export(category, categories_ext)
            return category_convert
        return response_error('could not get category parent to export')

    def get_category_id_import(self, convert, category, categories_ext):
        return category['term_id']

    def check_category_import(self, convert, category, categories_ext):
        id_imported = self.get_map_field_by_src(self.TYPE_CATEGORY, convert['id'], convert['code'],
                                                lang=self._notice['target']['language_default'])
        return True if id_imported else False

    def router_category_import(self, convert, category, categories_ext):
        return response_success('category_import')

    def before_category_import(self, convert, category, categories_ext):
        return response_success()

    def category_import(self, convert, category, categories_ext):
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code or (self.is_polylang() and not language_code):
            language_code = self._notice['target']['language_default']
        parent_id = 0
        slug_name = convert['url_key'] if convert.get('url_key') else (
            convert['code'] if convert['code'] and convert['id'] else (
                convert['name'].lower() if convert['name'] else ''))
        slug = self.sanitize_title(slug_name.replace("  ", " "))
        if slug:
            while self.rf_check_category_slug_exist(slug):
                if self.is_wpml():
                    if to_str(slug).endswith(f'-{to_str(language_code)}'):
                        slug = to_str(slug) + to_str(to_int(time.time()))
                    else:
                        slug = to_str(slug) + "-" + to_str(language_code)
                else:
                    slug = to_str(slug) + to_str(to_int(time.time()))

        if convert['parent'] and (convert['parent']['id'] or convert['parent']['code']):
            parent_import = self.import_category_parent(convert['parent'], language_code)
            if parent_import['result'] == 'success':
                parent_id = self.get_map_field_by_src(
                    self.TYPE_CATEGORY if not self.blog_running else self.TYPE_CATEGORY_BLOG, convert['parent']['id'],
                    to_str(convert['parent']['code']), language_code, 'value')
        category_term = {
            'name': self.strip_html_tag(convert['name']),
            'slug': slug,
            'term_group': 0,
        }
        category_term_query = self.create_insert_query_connector('terms', category_term)
        term_id = self.import_data_connector(category_term_query, 'category')
        if not term_id:
            return response_warning('category ' + to_str(convert['id']) + ' import false.')
        category_taxonomy = {
            'term_id': term_id,
            'taxonomy': 'product_cat' if not convert.get('is_blog') else 'category',
            'description': self.change_img_src_in_text(get_value_by_key_in_dict(convert, 'description', '')),
            'parent': parent_id if parent_id else 0,
            'count': convert['sort_order']
        }
        category_taxonomy_query = self.create_insert_query_connector('term_taxonomy', category_taxonomy)
        category_term_import = self.import_category_data_connector(category_taxonomy_query, True, convert['id'])
        if not category_term_import:
            return response_warning('category ' + to_str(convert['id']) + ' import false.')
        self.insert_map(self.TYPE_CATEGORY if not self.blog_running else self.TYPE_CATEGORY_BLOG, convert['id'],
                        category_term_import, to_str(convert['code']), slug, term_id, language_code)
        taxonomy_meta_table = 'termmeta'
        all_queries = list()
        meta_display_insert = {
            'term_id': term_id,
            'meta_key': 'display_type',
            'meta_value': convert.get('display_type', '')
        }
        all_queries.append(self.create_insert_query_connector(taxonomy_meta_table, meta_display_insert))
        thumbnail_id = False
        if convert['thumb_image']['url'] or convert['thumb_image']['path']:
            image_process = self.process_image_before_import(convert['thumb_image']['url'],
                                                             convert['thumb_image']['path'])
            config_image_path = self._notice['target']['config']['image_category'].rstrip('/') if not \
                self._notice['target']['config'].get('site_id') else self._notice['target']['config'][
                                                                         'image_category'].rstrip(
                '/') + '/sites/' + to_str(
                self._notice['target']['config']['site_id'])
            image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                self.make_woocommerce_image_path(image_process['path'], 'category'), config_image_path))
            if image_import_path:
                cate_image = self.remove_prefix_path(image_import_path,
                                                     self._notice['target']['config']['image_category'])
                _, image_details = self.get_sizes(image_process['url'])
                thumbnail_id = self.wp_image(cate_image, image_details, convert=convert)
        if thumbnail_id:
            meta_insert = {
                'term_id': term_id,
                'meta_key': 'thumbnail_id',
                'meta_value': thumbnail_id
            }
            all_queries.append(self.create_insert_query_connector(taxonomy_meta_table, meta_insert))
        if self.is_exist_lecm_rewrite():
            if (self._notice['config']['seo'] or self._notice['config']['seo_301']) and convert['seo']:
                # all_queries = list()
                for seo_url in convert['seo']:
                    # if not seo_url['request_path']:
                    # 	continue
                    # if slug != seo_url['request_path'].replace(' ', ''):
                    if seo_url['request_path']:
                        query_check = {
                            'link': seo_url['request_path']
                        }
                        if self.is_wpml() and convert.get('language_code'):
                            query_check['lang'] = convert['language_code']
                        seo_query = {
                            'type': 'select',
                            'query': "SELECT * FROM _DBPRF_lecm_rewrite WHERE " + self.dict_to_where_condition(
                                query_check)
                        }
                        check_seo_exit = self.select_data_connector(seo_query, 'category')
                        if check_seo_exit and check_seo_exit['result'] == 'success' and check_seo_exit[
                            'data'] and to_len(check_seo_exit['data']) > 0:
                            continue
                        else:
                            le_url_rewrite = {
                                'link': to_str(seo_url['request_path'].replace(' ', '')).strip('/'),
                                'type': 'category',
                                'type_id': term_id
                            }
                            if self.is_wpml():
                                le_url_rewrite['lang'] = convert.get('language_code')
                            if self._notice['config']['seo_301']:
                                le_url_rewrite['redirect_type'] = 301
                            self.import_data_connector(
                                self.create_insert_query_connector("lecm_rewrite", le_url_rewrite), 'seo_category')

        if self.is_wpml() or self._notice['target']['support']['yoast_seo']:
            query_wpseo = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_options` WHERE `option_name` = 'wpseo_taxonomy_meta'"
            }
            options_data = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query_wpseo)})
            if options_data and options_data['data']:
                option_value = php_unserialize(options_data['data'][0]['option_value'])
                if not option_value:
                    option_value = dict()
                if 'product_cat' not in option_value:
                    option_value['product_cat'] = dict()
                option_value['product_cat'][to_int(term_id)] = {
                    'wpseo_desc': get_value_by_key_in_dict(convert, 'meta_description', ''),
                    'wpseo_focuskw': get_value_by_key_in_dict(convert, 'meta_keyword', ''),
                    'wpseo_title': get_value_by_key_in_dict(convert, 'meta_title', '')
                }
                data_set = {
                    'option_value': php_serialize(option_value)
                }
                where = {
                    'option_id': options_data['data'][0]['option_id'],
                    'option_name': 'wpseo_taxonomy_meta'
                }
                update_query = self.create_update_query_connector('options', data_set, where)
                all_queries.append(update_query)
            else:
                new_option_data = {
                    'option_name': 'wpseo_taxonomy_meta',
                    'option_value': php_serialize({
                        'product_cat': {
                            to_int(term_id): {
                                'wpseo_desc': convert['meta_description'],
                                'wpseo_focuskw': convert['meta_keyword'],
                                'wpseo_title': convert['meta_title']
                            }
                        }
                    }),
                    'autoload': 'yes'
                }
                all_queries.append(self.create_insert_query_connector('options', new_option_data))
        if all_queries:
            self.import_multiple_data_connector(all_queries, 'category')
        return response_success(category_term_import)

    def get_new_trid(self):
        query = {
            'type': 'select',
            'query': "SELECT max(trid) as trid FROM _DBPRF_icl_translations"
        }
        trid = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        new_trid = 1
        if trid['data']:
            new_trid = to_int(trid['data'][0]['trid']) + 1
        return new_trid

    def after_category_import(self, category_id, convert, category, categories_ext):
        if self.is_wpml():
            source_language_code = self._notice['target']['language_default']
            language_code = convert.get('language_code')
            if not language_code:
                language_code = source_language_code
                source_language_code = None
            trid = convert.get('trid')
            if not trid:
                trid = self.get_new_trid()
            wpml_default = {
                'element_type': 'tax_product_cat',
                'element_id': category_id,
                'trid': trid,
                'language_code': language_code,
                'source_language_code': source_language_code
            }
            wpml_default_query = self.create_insert_query_connector("icl_translations", wpml_default)
            wpml_default = self.import_data_connector(wpml_default_query, 'category')
            # cate lang
            if not convert.get('language_code'):
                list_target_id = list()
                for src_language_id, target_language_id in self._notice['map']['languages'].items():
                    if target_language_id in list_target_id or to_str(target_language_id) == to_str(
                            self._notice['target']['language_default']):
                        continue
                    list_target_id.append(target_language_id)
                    category_lang = self.get_convert_data_language(convert, src_language_id)
                    category_lang['trid'] = trid
                    category_lang['language_code'] = target_language_id
                    category_import = self.category_import(category_lang, category, categories_ext)
                    if category_import['result'] == 'success':
                        self.after_category_import(category_import['data'], category_lang, category, categories_ext)
        if self.is_polylang():
            source_language_code = self._notice['target']['language_default']
            language_code = convert.get('language_code')
            if not language_code:
                language_code = source_language_code
                source_language_code = None
            term_id = self.get_map_field_by_src(self.TYPE_CATEGORY, convert['id'], None, language_code, 'value')
            if not term_id:
                return response_warning('category ' + to_str(convert['id']) + ' import false.')

            taxonomy_lang_id = self.get_map_field_by_src('category_lang', convert['id'])
            if not taxonomy_lang_id:
                term_data = {
                    'name': 'pll_' + to_str(term_id),
                    'slug': 'pll_' + to_str(term_id),
                    'term_group': 0,
                }
                term_query = self.create_insert_query_connector('terms', term_data)
                term_lang_id = self.import_data_connector(term_query, 'category')
                if not term_lang_id:
                    return response_warning('category ' + to_str(convert['id']) + ' import false.')
                def_data = {
                    language_code: term_id
                }
                term_taxonomy_data = {
                    'term_id': term_lang_id,
                    'taxonomy': 'term_translations',
                    'description': php_serialize(def_data),
                    'parent': 0,
                    'count': 0,
                }
                term_taxonomy_query = self.create_insert_query_connector('term_taxonomy', term_taxonomy_data)
                taxonomy_lang_id = self.import_data_connector(term_taxonomy_query, 'category')
                self.insert_map('category_lang', convert['id'], taxonomy_lang_id)
            if not taxonomy_lang_id:
                return response_warning('category ' + to_str(convert['id']) + ' not lang.')
            if taxonomy_lang_id:
                all_queries = list()
                query_lang = {
                    'type': 'select',
                    'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE `taxonomy` = 'term_translations' AND term_taxonomy_id = " + to_str(
                        taxonomy_lang_id)
                }
                cate_lang_data = self.get_connector_data(self.get_connector_url('query'),
                                                         {'query': json.dumps(query_lang)})
                if cate_lang_data and cate_lang_data['data']:
                    lang_value = php_unserialize(cate_lang_data['data'][0]['description'])
                    if not lang_value:
                        lang_value = dict()
                    if not language_code in lang_value:
                        lang_value[language_code] = term_id
                    data_set = {
                        'description': php_serialize(lang_value)
                    }
                    where = {
                        'taxonomy': 'term_translations',
                        'term_taxonomy_id': taxonomy_lang_id
                    }
                    update_query = self.create_update_query_connector('term_taxonomy', data_set, where)
                    all_queries.append(update_query)
                    term_relationships = {
                        'object_id': term_id,
                        'term_taxonomy_id': taxonomy_lang_id,
                        'term_order': 0,
                    }
                    term_relationships_lang = self.create_insert_query_connector('term_relationships',
                                                                                 term_relationships)
                    all_queries.append(term_relationships_lang)

                    relation_lang_code = {
                        'object_id': term_id,
                        'term_taxonomy_id': self._notice['target']['support']['polylang_category'].get(language_code,
                                                                                                       0),
                        'term_order': 0,
                    }
                    relation_lang_code_query = self.create_insert_query_connector('term_relationships',
                                                                                  relation_lang_code)
                    all_queries.append(relation_lang_code_query)
                    if all_queries:
                        self.import_multiple_data_connector(all_queries, 'category')

            if not convert.get('language_code'):
                list_target_id = list()
                for src_language_id, target_language_id in self._notice['map']['languages'].items():
                    if target_language_id in list_target_id or to_str(target_language_id) == to_str(
                            self._notice['target']['language_default']) or not convert['languages'].get(
                        src_language_id):
                        continue
                    list_target_id.append(target_language_id)
                    category_lang = self.get_convert_data_language(convert, src_language_id)
                    category_lang['language_code'] = target_language_id
                    category_import = self.category_import(category_lang, category, categories_ext)
                    if category_import['result'] == 'success':
                        self.after_category_import(category_import['data'], category_lang, category, categories_ext)
        # category_lang = convert['languages'][src_language_id] if src_language_id in convert[
        # 	'languages'] else None
        # if not category_lang or (src_language_id == get_value_by_key_in_dict(convert, 'language_default', self._notice['src']['language_default'])):
        # 	continue
        # cat_data_name = self.strip_html_tag(category_lang['name'])
        # cat_data_desc = self.change_img_src_in_text(category_lang['description'])
        # slug = self.sanitize_title(category_lang['name'])
        # cat_data = {
        # 	'name': cat_data_name,
        # 	'slug': slug,
        # 	'term_group': 0
        # }
        # term_id = self.import_data_connector(self.create_insert_query_connector('terms', cat_data), 'category')
        # if term_id:
        # 	parent_id = 0
        # 	if convert['parent']['id'] or convert['parent']['code']:
        # 		parent_id = self.get_map_field_by_src(self.TYPE_CATEGORY, convert['parent']['id'], to_str(convert['parent']['code']) + '-' + to_str(src_language_id), 'value')
        # 	term_taxonomy_data = {
        # 		'term_id': term_id,
        # 		'taxonomy': 'product_cat',
        # 		'description': cat_data_desc if cat_data_desc else ' ',
        # 		'parent': parent_id if parent_id else 0,
        # 		'count': 0,
        # 	}
        # 	term_taxonomy_id = self.import_data_connector(
        # 		self.create_insert_query_connector("term_taxonomy", term_taxonomy_data), 'category')
        #
        # 	meta_display_insert = {
        # 		'term_id': term_id,
        # 		'meta_key': 'display_type',
        # 		'meta_value': ''
        # 	}
        # 	meta_display_query = self.import_data_connector(
        # 		self.create_insert_query_connector("termmeta", meta_display_insert), 'category')
        #
        # 	thumbnail_id = False
        # 	if convert['thumb_image']['url'] or convert['thumb_image']['path']:
        # 		image_process = self.process_image_before_import(convert['thumb_image']['url'], convert['thumb_image']['path'])
        # 		image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(self.make_woocommerce_image_path(image_process['path']), self._notice['target']['config']['image_category'].rstrip('/')), 'category')
        # 		if image_import_path:
        # 			cate_image = self.remove_prefix_path(image_import_path, self._notice['target']['config']['image_category'])
        # 			thumbnail_id = self.wp_image(cate_image)
        # 	if thumbnail_id:
        # 		meta_insert = {
        # 			'term_id': term_id,
        # 			'meta_key': 'thumbnail_id',
        # 			'meta_value': thumbnail_id
        # 		}
        # 		termmeta_query = self.import_data_connector(
        # 			self.create_insert_query_connector("termmeta", meta_insert), 'category')
        #
        # 	if term_taxonomy_id:
        # 		self.insert_map(self.TYPE_CATEGORY, get_value_by_key_in_dict(category_lang, 'id', convert['id']), term_taxonomy_id, to_str(get_value_by_key_in_dict(category_lang, 'code', convert['code'])) + '-' + to_str(src_language_id), slug, term_id)
        # 		wpml_default = {
        # 			'element_type': 'tax_product_cat',
        # 			'element_id': term_taxonomy_id,
        # 			'trid': new_trid,
        # 			'language_code': target_language_id,
        # 			'source_language_code': get_value_by_key_in_dict(self._notice['map']['languages'], get_value_by_key_in_dict(convert, 'language_default', self._notice['src']['language_default']), self._notice['target']['language_default']),
        # 		}
        # 		wpml_default_query = self.create_insert_query_connector("icl_translations", wpml_default)
        # 		wpml_default = self.import_data_connector(wpml_default_query, 'category')
        return response_success()

    def addition_category_import(self, convert, category, categories_ext):
        return response_success()

    # TODO: PRODUCT
    def prepare_products_import(self):
        parent = super().prepare_products_import()
        if self._notice['config']['seo'] or self._notice['config']['seo_301']:
            query = self.dict_to_create_table_sql(self.lecm_rewrite_table_construct())
            self.query_data_connector({'type': 'query', 'query': query['query']})
        if not self._notice['config']['add_new']:
            file_name = get_pub_path() + '/media/' + to_str(self._migration_id) + '/variants.csv'
            if os.path.isfile(file_name):
                os.remove(file_name)
        return self

    def prepare_products_export(self):
        return self

    def get_products_main_export(self):
        id_src = self._notice['process']['products']['id_src']
        limit = self._notice['setting']['products']
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_posts WHERE ID > " + to_str(
                id_src) + " AND post_type = 'product' AND post_status NOT IN ('inherit','auto-draft') ORDER BY ID ASC LIMIT " + to_str(
                limit),
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_posts p LEFT JOIN _DBPRF_icl_translations il ON p.ID = il.element_id "
                         "WHERE il.`language_code` = '" + str(self.get_select_lang()) + "' and il.`element_type` = 'post_product' \
                         AND p.ID > " + to_str(id_src) + " AND p.post_type = 'product' AND p.post_status NOT IN ('inherit','auto-draft') \
                         ORDER BY p.ID ASC LIMIT " + to_str(limit),

            }
        products = self.select_data_connector(query, 'products')
        if not products or products['result'] != 'success':
            return response_error()
        return products

    def get_product_by_id(self, product_id):
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_posts WHERE ID = " + to_str(product_id),
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_posts p LEFT JOIN _DBPRF_icl_translations il ON p.ID = il.element_id "
                         "WHERE p.ID = " + to_str(product_id),

            }
        products = self.select_data_connector(query, 'products')
        if not products or products['result'] != 'success':
            return response_error()
        return products

    def get_products_ext_export(self, products):
        url_query = self.get_connector_url('query')
        product_ids = duplicate_field_value_from_list(products['data'], 'ID')
        product_id_con = self.list_to_in_condition(product_ids)
        # Felix
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations WHERE element_type = 'post_product' and element_id IN " + product_id_con

            }
            response = self.select_data_connector(query, 'product_languages')
            if response.get('result') == 'success' and response.get('data'):
                trids = duplicate_field_value_from_list(response['data'], 'trid')
                query = {
                    'type': 'select',
                    'query': "SELECT * FROM _DBPRF_icl_translations WHERE element_type = 'post_product' and trid IN " +
                    self.list_to_in_condition(trids)
                }
                response = self.select_data_connector(query, 'product_languages')
                if response.get('result') == 'success' and response.get('data'):
                    product_ids.extend(duplicate_field_value_from_list(response['data'], 'element_id'))
                    product_id_con = self.list_to_in_condition(list(set(product_ids)))
        # ----
        linked = self.product_to_in_condition_linked(product_ids)
        product_ext_queries = {
            'post_variant': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_posts WHERE post_type = 'product_variation' AND post_parent IN " + product_id_con,
            },
            'term_relationship': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_term_relationships AS tr "
                         "LEFT JOIN _DBPRF_term_taxonomy AS tx ON tx.term_taxonomy_id = tr.term_taxonomy_id "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                         "WHERE tr.object_id IN " + product_id_con,
            },
            'post_grouped': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_posts WHERE post_parent IN " + product_id_con + " AND post_type = 'product'",
            },
            'parent_link': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_postmeta WHERE meta_key IN ('_upsell_ids','_crosssell_ids') AND (meta_value " + linked + " )"
            },
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            product_ext_queries['icl_translations'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations WHERE element_type = 'post_product' and element_id IN " + product_id_con
            }

        products_ext = self.select_multiple_data_connector(product_ext_queries, 'products')
        if (not products_ext) or products_ext['result'] != 'success':
            return response_error()

        pro_child_ids = duplicate_field_value_from_list(products_ext['data']['post_variant'], 'ID')

        variant_id_query = self.list_to_in_condition(pro_child_ids)
        # Felix
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations WHERE element_type = 'post_product_variation' and element_id IN " + variant_id_query
            }
            post_product_variation = self.select_data_connector(query, 'post_product_variation')
            vr_trid = duplicate_field_value_from_list(post_product_variation['data'], 'trid')
            vr_trid_id_con = self.list_to_in_condition(vr_trid)


        taxonomy_duplicate = duplicate_field_value_from_list(products_ext['data']['term_relationship'], 'taxonomy')
        attrs_taxonomy = self.get_list_from_list_by_field_as_first_key(taxonomy_duplicate, '', 'pa_')

        attrs_name = list()
        for attr_taxonomy in attrs_taxonomy:
            attrs_name.append(self.substr_replace(attr_taxonomy, '', 0, 3))

        attr_name_query = self.list_to_in_condition(attrs_name)
        attr_values = duplicate_field_value_from_list(products_ext['data']['term_relationship'], 'term_id')
        attr_values_query = self.list_to_in_condition(attr_values)
        product_ext_rel_queries = {
            'woocommerce_attribute_taxonomies': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_woocommerce_attribute_taxonomies WHERE attribute_name IN " + attr_name_query,
            },
            'variation_term_relationship': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_term_relationships AS tr "
                         "LEFT JOIN _DBPRF_term_taxonomy AS tx ON tx.term_taxonomy_id = tr.term_taxonomy_id "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                         "WHERE tr.object_id IN " + variant_id_query,
            },
            'term_attribute': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_terms WHERE term_id IN " + attr_values_query,
            }
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            trids = duplicate_field_value_from_list(products_ext['data']['icl_translations'], 'trid')
            product_ext_rel_queries['wpml_product_lang'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations il "
                         "LEFT JOIN _DBPRF_posts as p ON il.element_id = p.ID "
                         "WHERE il.element_type = 'post_product' and il.trid IN " + self.list_to_in_condition(trids)
            }
            product_ext_rel_queries['wpml_variants_lang'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations il "
                         "LEFT JOIN _DBPRF_posts as p ON il.element_id = p.ID "
                         "WHERE il.element_type = 'post_product_variation' and il.trid IN " + vr_trid_id_con
            }

            product_ext_rel_queries['wpml_product_meta'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN (SELECT element_id FROM _DBPRF_icl_translations WHERE element_type = 'post_product' and trid IN " + self.list_to_in_condition(
                    trids) + ")"
            }

            product_ext_rel_queries['wpml_term_relationship'] = {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_term_relationships AS tr "
                         "LEFT JOIN _DBPRF_term_taxonomy AS tx ON tx.term_taxonomy_id = tr.term_taxonomy_id "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id WHERE tr.object_id IN (SELECT element_id FROM _DBPRF_icl_translations WHERE element_type = 'post_product' and trid IN " + self.list_to_in_condition(
                    trids) + ")",
            }

            product_ext_rel_queries['attributes_icl_translations'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_icl_translations il "
                         "LEFT JOIN _DBPRF_term_taxonomy as tx ON il.element_id = tx.term_id "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tx.term_id "
                         "WHERE il.element_type IN " + self.wpml_attributes_to_in_condition(attrs_taxonomy)
            }

        products_ext_rel = self.select_multiple_data_connector(product_ext_rel_queries, 'products')
        if (not products_ext_rel) or products_ext_rel['result'] != 'success':
            return response_error()
        try:
            vr_ids = duplicate_field_value_from_list(products_ext_rel['data']['wpml_variants_lang'], 'element_id')
            all_product_ids = self.list_to_in_condition(list(set(pro_child_ids + product_ids + vr_ids)))
        except:
            all_product_ids = self.list_to_in_condition(list(set(pro_child_ids + product_ids)))
        product_ext_rel_fourth_queries = {
            'post_meta': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN  " + all_product_ids,
            }
        }
        products_ext_fourth = self.get_connector_data(url_query, {
            'serialize': True, 'query': json.dumps(product_ext_rel_fourth_queries)
        })
        if (not products_ext_fourth) or products_ext_fourth['result'] != 'success':
            return response_error()


        thumbnail_id_list = get_list_from_list_by_field(products_ext_fourth['data']['post_meta'], 'meta_key',
                                                        '_thumbnail_id')
        thumbnail_ids = duplicate_field_value_from_list(thumbnail_id_list, 'meta_value')
        gallery_ids = gallery_ids_src = list()
        gallery_list = get_list_from_list_by_field(products_ext_fourth['data']['post_meta'], 'meta_key',
                                                   '_product_image_gallery')
        if gallery_list:
            for gallery in gallery_list:
                if 'meta_value' in gallery and gallery['meta_value']:
                    images_ids = gallery['meta_value'].split(',')
                    if images_ids:
                        gallery_ids = list(set(gallery_ids + images_ids))

        for id in gallery_ids:
            if id != '':
                gallery_ids_src.append(id)

        all_images_ids = list(set(thumbnail_ids + gallery_ids_src))
        all_images_ids_query = self.list_to_in_condition(all_images_ids)
        product_ext_rel_third_queries = {
            'image': {
                'type': 'select',
                'query': "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM _DBPRF_posts AS p "
                         "LEFT JOIN _DBPRF_postmeta AS pm ON pm.post_id = p.ID AND pm.meta_key = '_wp_attached_file' "
                         "WHERE p.ID IN " + all_images_ids_query,
            }
        }
        products_ext_third = self.get_connector_data(url_query, {
            'serialize': True, 'query': json.dumps(product_ext_rel_third_queries)
        })
        if (not products_ext_third) or products_ext_third['result'] != 'success':
            return response_error()



        products_ext2 = self.sync_connector_object(products_ext_rel, products_ext_fourth)
        products_ext1 = self.sync_connector_object(products_ext_rel, products_ext_third)
        products_ext = self.sync_connector_object(products_ext, products_ext1)
        products_ext = self.sync_connector_object(products_ext, products_ext2)
        return products_ext

    def convert_product_attributes(self, product, products_ext, product_meta, **kwargs):
        """
        Convert product attribute.

        Return: product_data, attribute_variants
        """
        product_data = {
            'attributes': list()
        }

        product_attribute = get_row_value_from_list_by_field(product_meta, 'meta_key', '_product_attributes',
                                                             'meta_value')
        product_attribute = php_unserialize(product_attribute)
        if isinstance(product_attribute, str):
            product_attribute = php_unserialize(product_attribute)
        src_option_values = get_list_from_list_by_field(products_ext['data']['term_relationship'], 'object_id',
                                                        product['ID'])
        attribute_variants = list()
        if product_attribute:
            for attribute_key, attribute in product_attribute.items():
                if to_int(attribute.get('is_taxonomy')) > 0:
                    woo_attribute = get_row_from_list_by_field(products_ext['data']['woocommerce_attribute_taxonomies'],
                                                               'attribute_name', to_str(attribute_key).replace('pa_', ''))
                    if not woo_attribute:
                        woo_attribute = get_row_from_list_by_field(
                            products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name',
                            to_str(attribute['name']).replace('pa_', ''))
                else:
                    woo_attribute = None
                if woo_attribute:
                    # attributes
                    attribute_data = self.construct_product_attribute()
                    attribute_data['option_id'] = woo_attribute['attribute_id']
                    option_code = to_str(woo_attribute['attribute_name']).lower()
                    attribute_data['option_code'] = option_code.strip()
                    attribute_data['option_type'] = woo_attribute['attribute_type']
                    attribute_data['option_name'] = woo_attribute['attribute_label']
                    attribute_data['option_group'] = woo_attribute['attribute_orderby']
                    attribute_data['is_visible'] = attribute.get('is_visible', 'visible')
                    attribute_data['is_variation'] = to_int(attribute.get('is_variation')) == 1
                    attribute_data['is_taxonomy'] = to_int(attribute.get('is_taxonomy')) == 1
                    for option_value in src_option_values:
                        attribute_name = 'pa_' + to_str(woo_attribute['attribute_name']).lower()
                        if 'taxonomy' in option_value:
                            if option_value['taxonomy'] == attribute_name:
                                woo_term_values = get_list_from_list_by_field(
                                    products_ext['data']['term_attribute'], 'term_id', option_value['term_id'])
                                if woo_term_values:
                                    attr_values = [x.get('name', '') for x in woo_term_values]
                                    attribute_data['option_value_name'] = ';'.join(attr_values)
                                    break
                    # attribute languages
                    if self.is_wpml():
                        attribute_icl_translations = products_ext['data']['attributes_icl_translations']
                        languages = duplicate_field_value_from_list(attribute_icl_translations, 'language_code')
                    else:
                        languages = [self._notice[self.get_type()]['language_default']]
                        attribute_icl_translations = []
                    attribute_language_data = self.construct_product_option_lang()
                    for language_id in languages:

                        attribute_language_data['option_name'] = woo_attribute['attribute_label']
                        attribute_data['option_languages'][language_id] = attribute_language_data
                        # attribute values
                        tmp_values = list()
                        desc = list()
                        if self.is_wpml():
                            for option_value in src_option_values:
                                attribute_name = 'pa_' + to_str(woo_attribute['attribute_name']).lower()
                                if 'taxonomy' in option_value:
                                    if option_value['taxonomy'] == attribute_name:
                                        woo_term_values = get_list_from_list_by_field(
                                            products_ext['data']['term_attribute'], 'term_id', option_value['term_id'])

                                        if woo_term_values:
                                            rf_trid = [term.get('term_id') for term in woo_term_values]
                                            value_language = copy.deepcopy(woo_term_values)
                                            for rf_id in rf_trid:
                                                trid = get_row_value_from_list_by_field(
                                                    attribute_icl_translations, 'element_id', rf_id, 'trid')
                                                if trid:
                                                    values = get_list_from_list_by_field(attribute_icl_translations, 'trid', trid)
                                                else:
                                                    values = woo_term_values
                                                value_language = get_list_from_list_by_field(values, 'language_code', language_id) or values

                                            for woo_term in value_language:
                                                attribute_value = woo_term['name']
                                                if woo_attribute['attribute_type'] in ['select', 'alg_wc_civs_image', 'image']:
                                                    option_values = to_str(woo_term['name']).split('|')
                                                    if option_values and to_len(option_values) > 1:
                                                        attribute_value = ';'.join(option_values)
                                                    tmp_values.append(attribute_value)
                                                desc.append(woo_term.get('description', ''))
                        else:
                            for option_value in src_option_values:
                                attribute_name = 'pa_' + to_str(woo_attribute['attribute_name']).lower()
                                if 'taxonomy' in option_value:
                                    if option_value['taxonomy'] == attribute_name:
                                        woo_term_values = get_list_from_list_by_field(
                                            products_ext['data']['term_attribute'], 'term_id', option_value['term_id'])
                                        if woo_term_values:
                                            for woo_term in woo_term_values:
                                                attribute_value = woo_term['name']
                                                if woo_attribute['attribute_type'] in ['select', 'alg_wc_civs_image',
                                                                                       'image', 'button', 'color']:
                                                    option_values = to_str(woo_term['name']).split('|')
                                                    if option_values and to_len(option_values) > 1:
                                                        attribute_value = ';'.join(option_values)
                                                    tmp_values.append(attribute_value)
                                                else:
                                                    tmp_values.append(attribute_value)
                                                desc.append(option_value['description'])

                        values = [x.strip() for x in tmp_values]

                        if values and to_len(values) > 1:
                            attribute_data['option_type'] = self.OPTION_MULTISELECT
                            if language_id == self._notice['src']['language_default']:
                                attribute_data['option_value_name'] = ';'.join(values)
                                attribute_data['option_value_description'] = ';'.join(desc)
                        attribute_data['option_value_languages'][language_id] = {
                            'option_value_name': ';'.join(values)
                        }

                    if (to_int(attribute.get('is_variation')) == 1 or to_str(
                            attribute.get('variation')) == 'yes') and not self.is_woo2woo():
                        attribute_variants.append(copy.deepcopy(attribute_data))
                    else:
                        product_data['attributes'].append(copy.deepcopy(attribute_data))
                else:
                    # special attribute products
                    language_product_attributes = dict()
                    if self.is_wpml():
                        trid = get_row_value_from_list_by_field(products_ext['data']['icl_translations'], 'element_id', product['ID'], 'trid')
                        if trid:
                            language_datas = get_list_from_list_by_field(products_ext['data']['wpml_product_lang'], 'trid', trid)
                            if language_datas:
                                for language_data in language_datas:
                                    meta_language_datas = get_list_from_list_by_field(products_ext['data']['wpml_product_meta'],'post_id', language_data['ID'])
                                    rf_product_attribute = php_unserialize(self.get_value_metadata(meta_language_datas,'_product_attributes', ''))
                                    if rf_product_attribute:
                                        language_product_attributes[language_data['language_code']] = rf_product_attribute
                    else:
                        language_product_attributes[self._notice[self.get_type()]['language_default']] =  \
                            php_unserialize(self.get_value_metadata(product_meta, '_product_attributes', ''))

                    if ('is_visible' in attribute and to_int(attribute['is_visible']) == 1) or (
                            'visible' in attribute and attribute['visible'] == 'yes'):
                        attribute_data = self.construct_product_attribute()
                        attribute_data['option_id'] = None
                        option_code = to_str(attribute['name']).lower()
                        attribute_data['option_code'] = option_code.lower().strip()
                        attribute_data['option_type'] = 'text'
                        attribute_data['option_name'] = attribute['name']
                        attribute_data['option_group'] = 'menu_order'
                        attribute_data['is_visible'] = attribute.get('is_visible', 'visible')
                        attribute_data['is_variation'] = to_int(attribute.get('is_variation')) == 1
                        # attribute language
                        attribute_values = dict()
                        for language_id, meta_data in language_product_attributes.items():
                            if meta_data.get(attribute_key):
                                attribute_values[language_id] = meta_data[attribute_key]

                        for language_id, attribute_row in attribute_values.items():
                            attribute_language_data = self.construct_product_option_lang()
                            attribute_language_data['option_name'] = attribute_row['name']
                            attribute_data['option_languages'][language_id] = copy.deepcopy(attribute_language_data)

                            # rf_attribute values
                            attribute_value = attribute_row['value']
                            if attribute_value and attribute_value != '':
                                option_values = list()
                                if isinstance(attribute_value, dict):
                                    for key, attr_value in attribute_value.items():
                                        option_values.append(attr_value)
                                else:
                                    option_values = attribute_value.split('|')
                                if option_values and to_len(option_values) > 1:
                                    attribute_data['option_type'] = 'multiselect'
                                    option_values = list(map(lambda x: x.strip(), option_values))
                                    attribute_value = ';'.join(option_values)
                            if language_id == self._notice['src']['language_default']:
                                attribute_data['option_value_name'] = attribute_value
                            attribute_data['option_value_languages'][language_id] = {
                                    'option_value_name': attribute_value}

                        if (to_int(attribute.get('is_variation')) == 1 or to_str(
                                attribute.get('variation')) == 'yes') and not self.is_woo2woo():
                            attribute_data['option_type'] = 'select'
                            attribute_variants.append(copy.deepcopy(attribute_data))
                        else:
                            product_data['attributes'].append(copy.deepcopy(attribute_data))
        return product_data, attribute_variants

    def convert_product_languages(self, product, products_ext, **kwargs):
        """
        Support WPML.
        Convert products for each language.
        Fields:
            [
                name,
                description,
                short_description,
                meta_title : SEO title (*support Yoast SEO Plug-in.),
                meta_keyword,
                meta_description,
                code,
                price
            ]
        Return:
            {
                'language_default': xx
                'languages': {
                    ...Fields
                },

            }
        """
        product_data = {
            'languages': dict()
        }
        if self._notice['src']['support'][PluginSupport.wpml.name]:
            trid = get_row_value_from_list_by_field(products_ext['data']['icl_translations'], 'element_id',
                                                    product['ID'], 'trid')
            if trid:
                language_datas = get_list_from_list_by_field(products_ext['data']['wpml_product_lang'], 'trid', trid)
                if language_datas:
                    for language_data in language_datas:
                        if not language_data['post_title']:
                            continue
                        meta_language_datas = get_list_from_list_by_field(products_ext['data']['wpml_product_meta'],
                                                                          'post_id', language_data['ID'])
                        term_relationship_language = get_list_from_list_by_field(
                            products_ext['data']['wpml_term_relationship'], 'object_id', language_data['ID'])
                        product_new_data = self.construct_product_lang()

                        product_new_data['name'] = language_data['post_title']
                        product_new_data['code'] = language_data['post_name']
                        product_new_data['description'] = language_data['post_content']
                        product_new_data['short_description'] = language_data['post_excerpt']
                        product_new_data['meta_description'] = self.get_value_metadata(meta_language_datas,
                                                                                       '_yoast_wpseo_metadesc', '')
                        product_new_data['meta_keyword'] = self.get_value_metadata(meta_language_datas,
                                                                                   '_yoast_wpseo_focuskw', '')
                        product_new_data['meta_title'] = self.get_value_metadata(meta_language_datas,
                                                                                 '_yoast_wpseo_title', '')
                        if product_new_data['meta_title']:
                            product_new_data['meta_title'] = product_new_data['meta_title'].replace('%%title%%',
                                                                                                    product_new_data[
                                                                                                        'name']).replace(
                                '%%page%%', '').replace('%%sep%%', '-').replace('%%sitename%%', '')
                        wpml_product_tags = get_list_from_list_by_field(term_relationship_language, 'taxonomy',
                                                                        'product_tag')
                        if wpml_product_tags:
                            wpml_tags = list()
                            for wpml_product_tag in wpml_product_tags:
                                wpml_tags.append(wpml_product_tag['name'])
                            if wpml_tags:
                                product_new_data['tags'] = ','.join(wpml_tags)

                        if not language_data['source_language_code']:
                            product_data['language_default'] = language_data['language_code']
                        product_data['languages'][language_data['language_code']] = product_new_data
        else:
            product_language_data = self.construct_product_lang()
            product_language_data['name'] = product['post_title']
            product_language_data['description'] = product['post_content']
            product_language_data['short_description'] = product['post_excerpt']
            language_id = self._notice['src']['language_default']
            product_data['languages'][language_id] = product_language_data
        return product_data

    def convert_product_export(self, product, products_ext):
        product_meta = get_list_from_list_by_field(products_ext['data']['post_meta'], 'post_id', product['ID'])
        product_data = self.construct_product()
        product_data = self.add_construct_default(product_data)
        product_data['id'] = product['ID']
        product_data['sku'] = self.get_value_metadata(product_meta, '_sku')

        # todo: get type prd virtual
        product_type = get_row_value_from_list_by_field(product_meta, 'meta_key', '_virtual', 'meta_value')
        if product_type == 'yes':
            product_data['type'] = 'virtual'

        product_price = ''
        if to_decimal(self.get_value_metadata(product_meta, '_regular_price', 0.0000)) > 0:
            product_price = self.get_value_metadata(product_meta, '_regular_price', 0.0000)
        else:
            product_price = self.get_value_metadata(product_meta, '_price', 0.0000)

        if product_price == '' or product_price == self.get_value_metadata(product_meta, '_min_variation_sale_price',
                                                                           0.0000):
            product_price = self.get_value_metadata(product_meta, '_min_variation_regular_price', 0.0000)

        if product_price == '' or not product_price:
            product_price = 0

        product_data['price'] = product_price
        product_data['weight'] = self.get_value_metadata(product_meta, '_weight', 0.0000)
        product_data['length'] = self.get_value_metadata(product_meta, '_length', 0.0000)
        product_data['width'] = self.get_value_metadata(product_meta, '_width', 0.0000)
        product_data['height'] = self.get_value_metadata(product_meta, '_height', 0.0000)
        product_data['status'] = product['post_status'] == "publish"
        product_data['manage_stock'] = True if self.get_value_metadata(product_meta, '_manage_stock',
                                                                       'no') == "yes" else False
        if self.is_woo2woo():
            product_data['is_in_stock'] = self.get_value_metadata(product_meta, '_stock_status', 'instock')
            product_data['sold_individually'] = self.get_value_metadata(product_meta, '_sold_individually', '')
            product_data['purchase_note'] = self.get_value_metadata(product_meta, '_purchase_note', '')
        else:
            product_data['is_in_stock'] = True if self.get_value_metadata(product_meta, '_stock_status',
                                                                          'instock') == "instock" else False
        product_data['qty'] = to_int(to_decimal(self.get_value_metadata(product_meta, '_stock', 0))) if to_decimal(
            self.get_value_metadata(product_meta, '_stock', 0)) > 0 else 0
        product_data['created_at'] = convert_format_time(product['post_date'])
        product_data['updated_at'] = convert_format_time(product['post_modified'])
        product_data['name'] = product['post_title']

        product_data['description'] = self.process_content(product['post_content'])
        product_data['short_description'] = self.process_content(product['post_excerpt'])

        product_data['menu_order'] = product['menu_order']
        product_data['sort_order'] = product['menu_order']
        product_data['backorders'] = self.get_value_metadata(product_meta, '_backorders', 'no')
        product_data['meta_description'] = self.get_value_metadata(product_meta, '_yoast_wpseo_metadesc', '')
        product_data['meta_title'] = self.get_value_metadata(product_meta, '_yoast_wpseo_title', '')
        if product_data['meta_title']:
            product_data['meta_title'] = product_data['meta_title'].replace('%%title%%', product_data['name']).replace(
                '%%page%%', '').replace('%%sep%%', '-').replace('%%sitename%%', '')
        # image_
        thumbnail_id = self.get_value_metadata(product_meta, '_thumbnail_id', 0)
        if thumbnail_id:
            thumbnail_src = get_list_from_list_by_field(products_ext['data']['image'], 'ID', thumbnail_id)
            if thumbnail_src:
                product_data['thumb_image']['label'] = thumbnail_src[0]['post_title']
                product_data['thumb_image']['url'] = "https://fabricfactory.mylittleshindig.com" + '/wp-content/uploads/' + to_str(thumbnail_src[0]['meta_value']).lstrip('/')
                product_data['thumb_image']['url'] = to_str(product_data['thumb_image']['url']).replace(
                    'uploads/uploads', 'uploads')
        gallery_ids = self.get_value_metadata(product_meta, '_product_image_gallery', '')
        if gallery_ids:
            gallery_ids = gallery_ids.split(',')
            for gallery_id in gallery_ids:
                image_gallery_src = get_list_from_list_by_field(products_ext['data']['image'], 'ID', gallery_id)
                product_image_data = self.construct_product_image()
                if image_gallery_src:
                    product_image_data['label'] = image_gallery_src[0]['post_title']
                    product_image_data['url'] = "https://fabricfactory.mylittleshindig.com" + '/wp-content/uploads/' + \
                                                image_gallery_src[0]['meta_value'].lstrip('/')
                    product_image_data['url'] = to_str(product_image_data['url']).replace('uploads/uploads', 'uploads')
                    product_data['images'].append(product_image_data)

        sale_price = self.get_value_metadata(product_meta, '_sale_price', '')
        if sale_price != '':
            product_data['special_price']['price'] = to_decimal(sale_price)
            start_date = self.get_value_metadata(product_meta, '_sale_price_dates_from', '')
            if start_date:
                product_data['special_price']['start_date'] = convert_format_time(start_date)
            end_date = self.get_value_metadata(product_meta, '_sale_price_dates_to', '')
            if end_date:
                product_data['special_price']['end_date'] = convert_format_time(
                    self.get_value_metadata(product_meta, '_sale_price_dates_to', ''))
        else:
            product_data['special_price']['price'] = self.get_value_metadata(product_meta, '_min_variation_sale_price',
                                                                             0.0000)

        if not product_data['special_price']['price']:
            product_data['special_price']['price'] = 0

        crosssell_ids = self.get_value_metadata(product_meta, '_crosssell_ids', '')
        if crosssell_ids:
            crosssell_ids_data = php_unserialize(crosssell_ids)
            if crosssell_ids_data:
                for crosssell_id in crosssell_ids_data:
                    relation = self.construct_product_relation()
                    relation['id'] = crosssell_id
                    relation['type'] = self.PRODUCT_CROSS
                    product_data['relate']['children'].append(relation)
        parent_crosssell_list = get_list_from_list_by_field(products_ext['data']['parent_link'], 'meta_key',
                                                            '_crosssell_ids')
        if parent_crosssell_list:
            for parent_crosssell in parent_crosssell_list:
                if parent_crosssell['meta_value'].find(':' + to_str(product['ID']) + ';') != -1:
                    relation = self.construct_product_relation()
                    relation['id'] = parent_crosssell['post_id']
                    relation['type'] = self.PRODUCT_CROSS
                    product_data['relate']['parent'].append(relation)
        upsell_ids = self.get_value_metadata(product_meta, '_upsell_ids', '')
        if upsell_ids:
            upsell_ids_data = php_unserialize(upsell_ids)
            if upsell_ids_data:
                for upsell_id in upsell_ids_data:
                    relation = self.construct_product_relation()
                    relation['id'] = upsell_id
                    relation['type'] = self.PRODUCT_UPSELL
                    product_data['relate']['children'].append(relation)
        parent_upsell_list = get_list_from_list_by_field(products_ext['data']['parent_link'], 'meta_key', '_upsell_ids')
        if parent_upsell_list:
            for parent_upsell in parent_upsell_list:
                if parent_upsell['meta_value'].find(':' + to_str(product['ID']) + ';') != -1:
                    relation = self.construct_product_relation()
                    relation['id'] = parent_upsell['post_id']
                    relation['type'] = self.PRODUCT_UPSELL
                    product_data['relate']['parent'].append(relation)
        product_data['tax']['code'] = self.get_value_metadata(product_meta, '_tax_class',
                                                              'standard') if self.get_value_metadata(product_meta,
                                                                                                     '_tax_status',
                                                                                                     'taxable') != 'none' else None
        product_data['tax']['status'] = self.get_value_metadata(product_meta, '_tax_status', 'taxable')
        # category product
        term_relationship = get_list_from_list_by_field(products_ext['data']['term_relationship'], 'object_id',
                                                        product['ID'])
        category_src = get_list_from_list_by_field(term_relationship, 'taxonomy', 'product_cat')
        if category_src:
            for product_category in category_src:
                product_category_data = self.construct_product_category()
                product_category_data['id'] = product_category['term_id']
                product_category_data['code'] = product_category['slug']
                product_data['categories'].append(product_category_data)
        # TODO Convert manufacture
        if self._notice['src']['support'][PluginSupport.manufacturers.name]:
            manu_src = get_row_from_list_by_field(term_relationship, 'taxonomy', 'product_brand')
            if not manu_src:
                manu_src = get_row_from_list_by_field(term_relationship, 'taxonomy', 'pwb-brand')
            if manu_src:
                product_manufacturer_data = dict()
                product_manufacturer_data['id'] = manu_src['term_id']
                product_manufacturer_data['name'] = manu_src['name']
                product_manufacturer_data['code'] = manu_src['slug']
                product_data['manufacturer'] = product_manufacturer_data
        # TODO Convert Tags
        product_tags = get_list_from_list_by_field(term_relationship, 'taxonomy', 'product_tag')
        if product_tags:
            tags = list()
            for product_tag in product_tags:
                tags.append(product_tag['name'])
            if tags:
                product_data['tags'] = ','.join(tags)

        # if self._notice['config']['seo']:
        detect_seo = self.detect_seo()
        product_data['seo'] = getattr(self, 'products_' + detect_seo)(product, products_ext)
        # TODO: convert product languages
        product_languages = self.convert_product_languages(product, products_ext)
        product_data.update(product_languages)

        # TODO: Attribute
        rf_product_attributes, attribute_variants = self.convert_product_attributes(product, products_ext, product_meta)
        product_data.update(rf_product_attributes)

        # todo: plugin add-ons
        if self._notice['src']['support'][PluginSupport.addons.name] and not self.is_woo2woo():
            product_addons = get_row_value_from_list_by_field(product_meta, 'meta_key', '_product_addons', 'meta_value')
            product_addons = php_unserialize(product_addons)
            if product_addons and to_len(product_addons) > 0:
                for product_addon in product_addons:
                    if not product_addon.get('options') or to_len(product_addon['options']) == 0:
                        continue
                    if product_addon.get('type') == 'radiobutton':
                        option_type = self.OPTION_RADIO
                    else:
                        option_type = self.OPTION_SELECT
                    product_option = self.construct_product_option()
                    product_option['code'] = self.convert_attribute_code(product_addon.get('name'))
                    product_option['option_code'] = self.convert_attribute_code(product_addon.get('name'))
                    product_option['option_name'] = product_addon.get('name')
                    product_option['type'] = option_type
                    product_option['position'] = product_addon.get('position')
                    product_option['required'] = True if product_addon.get('required') and to_int(
                        product_addon.get('required')) == 1 else False
                    product_addon_options = list()
                    if isinstance(product_addon.get('options'), dict):
                        for key, product_addon_value in product_addon['options'].items():
                            product_addon_options.append(product_addon_value)
                    else:
                        product_addon_options = product_addon.get('options')
                    for product_addon_value in product_addon_options:
                        product_option_value = self.construct_product_option_value()
                        product_option_value['code'] = self.convert_attribute_code(product_addon_value.get('label'))
                        product_option_value['option_value_code'] = self.convert_attribute_code(
                            product_addon_value.get('label'))
                        product_option_value['option_value_name'] = product_addon_value.get('label')
                        product_option_value['option_value_price'] = product_addon_value.get('price')
                        if 'Color' in product_addon.get('name', '') or 'Colour' in product_addon.get('name', ''):
                            if 'RNBP' in product_addon_value.get('label', ''):
                                product_option_value['thumb_image']['path'] = self.convert_attribute_code(
                                    to_str(product_addon_value.get('label')).replace(' (RNBP)', '')) + '.jpg'
                                product_option_value['thumb_image']['url'] = "https://fabricfactory.mylittleshindig.com" + '/assets/blind-images/rnbp/'
                        product_option['values'].append(product_option_value)
                    product_data['options'].append(product_option)

        # todo: downloadable
        product_downloadables = get_row_value_from_list_by_field(product_meta, 'meta_key', '_downloadable_files',
                                                                 'meta_value')
        product_downloadables = php_unserialize(product_downloadables)
        if product_downloadables and isinstance(product_downloadables, dict):
            product_data['type'] = self.PRODUCT_DOWNLOAD
            for key, product_downloadable in product_downloadables.items():
                download_data = self.construct_product_downloadable()
                download_data['limit'] = get_row_value_from_list_by_field(product_meta, 'meta_key', '_download_limit',
                                                                          'meta_value')
                download_data['max_day'] = get_row_value_from_list_by_field(product_meta, 'meta_key',
                                                                            '_download_expiry', 'meta_value')
                name_file = to_str(product_downloadable['file']).split('/') if product_downloadable.get(
                    'file') else None
                if "https://fabricfactory.mylittleshindig.com" in product_downloadable['file'] and name_file:
                    download_data['name'] = to_str(product_downloadable['file']).split('/')
                    download_data['path'] = 'woocommerce/' + to_str(name_file[to_len(name_file) - 1]).lower()
                else:
                    download_data['name'] = product_downloadable['name']
                    download_data['path'] = product_downloadable['file']
                # Thieu max_day,limit
                product_data['downloadable'].append(download_data)

        # todo: group product
        child_group_product = self.get_value_metadata(product_meta, '_children', '')
        if child_group_product:
            child_group_product = php_unserialize(child_group_product)
            if child_group_product and to_len(child_group_product) > 0:
                for child_group_product_id in child_group_product:
                    product_data['group_child_ids'].append({
                        'id': child_group_product_id
                    })
                product_data['type'] = self.PRODUCT_GROUP

        # todo: child product
        product_child_src = get_list_from_list_by_field(products_ext['data']['post_variant'], 'post_parent',
                                                        product['ID'])
        vr_ids = duplicate_field_value_from_list(product_child_src, 'ID')
        try:
            all_variants_default_lang = [variant for variant in products_ext['data']['wpml_variants_lang']
                                         if variant['element_id'] in vr_ids
                                         and variant['language_code'] == self._notice['src']['language_default']]
        except:
            all_variants_default_lang = get_list_from_list_by_field(products_ext['data']['post_variant'], 'post_parent', product['ID'])
        all_child = dict()
        child_attributes = dict()
        if product_child_src:
            product_data['type'] = self.PRODUCT_CONFIG
            for product_child in all_variants_default_lang:
                try:
                    variant_trid_lang = get_row_value_from_list_by_field(products_ext['data']['wpml_variants_lang'], 'element_id', product_child['ID'], 'trid')
                    variant_lang = get_list_from_list_by_field(products_ext['data']['wpml_variants_lang'],'trid', variant_trid_lang)
                except:
                    variant_lang = all_variants_default_lang
                # lang_default = self._notice['src']['language_default']

                child_attributes[product_child['ID']] = dict()
                child_data = self.construct_product_child()
                child_data = self.add_construct_default(child_data)
                child_meta = get_list_from_list_by_field(products_ext['data']['post_meta'], 'post_id',
                                                         product_child['ID'])
                child_data['id'] = product_child['ID']
                child_data['sku'] = self.get_value_metadata(child_meta, '_sku', self.get_value_metadata(product_meta, '_sku', ''))
                child_data['price'] = self.get_value_metadata(child_meta, '_regular_price', self.get_value_metadata(child_meta, '_price', 0.0000))
                child_data['weight'] = self.get_value_metadata(child_meta, '_weight', product_data['weight'])
                child_data['length'] = self.get_value_metadata(child_meta, '_length', product_data['length'])
                child_data['width'] = self.get_value_metadata(child_meta, '_width', product_data['width'])
                child_data['height'] = self.get_value_metadata(child_meta, '_height', product_data['height'])
                child_data['status'] = product_child['post_status'] == "publish"
                child_data['manage_stock'] = self.get_value_metadata(child_meta, '_manage_stock') == 'yes'
                if self.is_woo2woo():
                    child_data['is_in_stock'] = self.get_value_metadata(child_meta, '_stock_status', 'instock')
                    child_data['sold_individually'] = self.get_value_metadata(child_meta, '_sold_individually', '')
                    child_data['purchase_note'] = self.get_value_metadata(child_meta, '_purchase_note', '')
                else:
                    child_data['is_in_stock'] = self.get_value_metadata(child_meta, '_stock_status', 'instock') == "instock"
                child_data['qty'] = to_int(to_decimal(self.get_value_metadata(child_meta, '_stock', 0)))
                child_data['created_at'] = convert_format_time(product_child['post_date'])
                child_data['updated_at'] = convert_format_time(product_child['post_modified'])
                child_data['name'] = product_child['post_title']
                child_data['description'] = self.get_value_metadata(child_meta, '_variation_description')
                child_data['tax']['code'] = self.get_value_metadata(child_meta, '_tax_class', 'standard')
                child_data['short_description'] = ''
                # image
                thumbnail_id = self.get_value_metadata(child_meta, '_thumbnail_id')
                if thumbnail_id:
                    thumbnail_src = get_list_from_list_by_field(products_ext['data']['image'], 'ID', thumbnail_id)
                    if thumbnail_src:
                        child_data['thumb_image']['label'] = thumbnail_src[0]['post_title']
                        child_data['thumb_image']['path'] = thumbnail_src[0]['meta_value']
                        child_data['thumb_image']['url'] = to_str(thumbnail_src[0]['guid']).replace(
                            thumbnail_src[0]['meta_value'], '')

                sale_price = self.get_value_metadata(child_meta, '_sale_price', '')
                if sale_price != '':
                    child_data['special_price']['price'] = sale_price
                    child_data['special_price']['start_date'] = convert_format_time(
                        self.get_value_metadata(child_meta, '_sale_price_dates_from'))
                    child_data['special_price']['end_date'] = convert_format_time(
                        self.get_value_metadata(child_meta, '_sale_price_dates_to'))
                # TODO WPML for children
                for variant in variant_lang:
                    child_product_language_data = self.construct_product_lang()
                    child_product_language_data['name'] = variant['post_title']
                    child_meta_lang = get_list_from_list_by_field(products_ext['data']['post_meta'], 'post_id', variant['ID'])
                    child_product_language_data['description'] = self.get_value_metadata(child_meta_lang, '_variation_description')
                    child_product_language_data['short_description'] = variant['post_excerpt']
                    try:
                        language_id = variant['language_code']
                    except:
                        language_id = self._notice[self.get_type()]['language_default']
                    child_data['languages'][language_id] = copy.deepcopy(child_product_language_data)

                attr_child = self.get_list_from_list_by_field_as_first_key(child_meta, 'meta_key', 'attribute_')
                child_data['options'] = list()
                child_data['attributes'] = list()
                for attribute in attr_child:
                    attribute_child_data = self.construct_product_attribute()
                    attr_name = to_str(attribute['meta_key']).replace('attribute_', '')
                    element_type = 'tax_' + attr_name
                    attr_name = attr_name.replace('pa_', '')
                    attr_name = attr_name.strip()
                    option_id = get_row_value_from_list_by_field(
                        products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name', attr_name,'attribute_id')

                    attribute_child_data['option_id'] = option_id if option_id else ''
                    option_name = get_row_value_from_list_by_field(
                        products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name', attr_name,
                        'attribute_label')

                    attribute_child_data['option_name'] = option_name if option_name else attr_name
                    option_code = get_row_value_from_list_by_field(
                        products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name', attr_name,
                        'attribute_name')
                    attribute_child_data['option_code'] = option_code if option_code else attr_name.lower()
                    option_type = get_row_value_from_list_by_field(
                        products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name', attr_name,
                        'attribute_type')
                    # attribute_child_data['option_type'] = option_type if option_type else 'select'
                    attribute_child_data['option_type'] = self.OPTION_SELECT
                    option_group = get_row_value_from_list_by_field(
                        products_ext['data']['woocommerce_attribute_taxonomies'], 'attribute_name', attr_name, 'attribute_orderby')
                    attribute_child_data['option_group'] = option_group if option_group else 'menu_order'
                    # attribute language
                    for variant in variant_lang:
                        if 'language_code' not in variant:
                            variant['language_code'] = self._notice[self.get_type()]['language_default']
                        child_attribute_language_data = self.construct_product_option_lang()
                        child_attribute_language_data['option_name'] = attribute_child_data['option_name']
                        attribute_child_data['option_languages'][variant['language_code']] = copy.deepcopy(child_attribute_language_data)

                    # values
                    attribute_child_data['option_value_id'] = get_row_value_from_list_by_field(
                        products_ext['data']['term_attribute'], 'slug', attribute['meta_value'], 'term_id')
                    option_value_name = get_row_value_from_list_by_field(products_ext['data']['term_attribute'], 'slug',
                                                                         attribute['meta_value'], 'name')
                    attribute_child_data['option_value_name'] = get_row_value_from_list_by_field(
                        products_ext['data']['term_attribute'], 'slug', attribute['meta_value'],
                        'name') if get_row_value_from_list_by_field(products_ext['data']['term_attribute'], 'slug',
                                                                    attribute['meta_value'], 'name') else attribute[
                        'meta_value']
                    attribute_child_data['option_value_code'] = to_str(attribute['meta_value']).lower()
                    attribute_child_data['option_value_description'] = get_row_value_from_list_by_field(
                        products_ext['data']['term_relationship'], 'slug', attribute['meta_value'],
                        'description') if get_row_value_from_list_by_field(products_ext['data']['term_relationship'],
                                                                           'slug', attribute['meta_value'],
                                                                           'description') else ''
                    for variant in variant_lang:
                        if 'language_code' not in variant:
                            variant['language_code'] = self._notice[self.get_type()]['language_default']
                        child_meta_lang = get_list_from_list_by_field(products_ext['data']['post_meta'], 'post_id',
                                                                      variant['ID'])
                        attr_child_lang = self.get_list_from_list_by_field_as_first_key(child_meta_lang, 'meta_key', 'attribute_')
                        vr_attr = [attr for attr in attr_child_lang if attr['post_id'] == variant['ID'] and attr['meta_key'] == attribute['meta_key']]
                        if vr_attr:
                            vr_attr = vr_attr[0]
                        else:
                            vr_attr = {}

                        child_attribute_value_language_data = self.construct_product_option_value_lang()
                        child_attribute_value_language_data['option_value_name'] = get_row_value_from_list_by_field(
                        products_ext['data']['term_attribute'], 'slug', vr_attr['meta_value'],
                        'name') if get_row_value_from_list_by_field(products_ext['data']['term_attribute'], 'slug',
                                                                    vr_attr.get('meta_value'), 'name') else vr_attr.get('meta_value')
                        attribute_child_data['option_value_languages'][variant['language_code']] = child_attribute_value_language_data
                    child_data['attributes'].append(attribute_child_data)

                all_child[to_str(product_child['ID'])] = child_data

        # todo: bundle product - product bundle plugin: WPC Product Bundles for WooCommerce (Premium)
        if self._notice['src']['support']['product_bundle']:
            product_data['bundle_selection'] = list()
            product_bundles = get_row_value_from_list_by_field(product_meta, 'meta_key', 'woosb_ids', 'meta_value')
            if product_bundles:
                product_data['type'] = self.PRODUCT_BUNDLE
                product_bundle_list = to_str(product_bundles).split(',')
                if product_bundle_list and to_len(product_bundle_list) > 0:
                    for product_bundle_child in product_bundle_list:
                        product_bundle_ids = to_str(product_bundle_child).split('/')
                        if product_bundle_ids and to_len(product_bundle_ids) > 0:
                            product_bundle_data = {
                                'product_id': product_bundle_ids[0],
                                'selection_qty': product_bundle_ids[1] if to_len(product_bundle_ids) > 1 else 1
                            }
                            product_data['bundle_selection'].append(product_bundle_data)

        product_data['children'] = list(all_child.values())
        product_data['children'] = sorted(product_data['children'], key=lambda i: i['id'])

        return response_success(product_data)

    def get_product_id_import(self, convert, product, products_ext):
        return product['ID']

    def check_product_import(self, convert, product, products_ext):
        return self.get_map_field_by_src(self.TYPE_PRODUCT, convert['id'], convert['code'],
                                         lang=self._notice['target']['language_default'])

    def update_latest_data_product(self, product_id, convert, product, products_ext):
        all_query = list()
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code:
            language_code = self._notice['target']['language_default']
        # todo: update product name
        # begin
        product_query = self.create_update_query_connector("posts", {'ID': product_id, 'post_title': convert['name']},
                                                           {'ID': product_id})
        all_query.append(product_query)

        # end

        old_url_key = self.get_map_field_by_src(self.TYPE_PRODUCT, convert['id'], convert['code'], 'code_desc')

        # todo: update product category
        # begin
        category_desc = self.select_all_category_map()
        all_categories = list()
        for category in convert['categories']:
            category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'],
                                                    lang=language_code)
            if not category_id:
                category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, None, category['code'], lang=language_code)
            if not category_id:
                category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], None, lang=language_code)
            if category_id:
                all_categories.append(category_id)
        all_categories = list(set(all_categories))
        # todo: delete old category product
        query_cate = {
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_term_relationships` WHERE `object_id` = " + to_str(
                product_id) + " AND `term_taxonomy_id` IN " + self.list_to_in_condition(category_desc) + ""
        }
        self.query_data_connector(query_cate, 'update_product')
        for cate_id in all_categories:
            query_cate_prod = {
                'type': 'select',
                'query': "SELECT * FROM `_DBPRF_term_relationships` WHERE `object_id` = " + to_str(
                    product_id) + " AND `term_taxonomy_id` = " + to_str(cate_id) + ""
            }
            check_product_category = self.select_data_connector(query_cate_prod, 'category_product')
            if (not check_product_category) or check_product_category['result'] != 'success' or (
                    to_len(check_product_category['data']) == 0):
                category_data = {
                    'object_id': product_id,
                    'term_taxonomy_id': cate_id,
                    'term_order': 0
                }
                category_query = self.create_insert_query_connector("term_relationships", category_data)
                all_query.append(category_query)

        # End
        stock_status = 'instock'
        if 'is_in_stock' in convert:
            stock_status = 'instock' if convert['is_in_stock'] else 'outofstock'
        else:
            stock_status = 'outofstock' if convert['manage_stock'] else 'instock'
        tax_class = ''
        if convert['tax']['id'] or convert['tax']['code']:
            tax_class = self.get_map_field_by_src(self.TYPE_TAX, convert['tax']['id'], convert['tax']['code'],
                                                  field='code_desc')
        product_meta = {
            '_stock_status': stock_status,
            '_downloadable': "yes" if convert['type'] == self.PRODUCT_DOWNLOAD else "no",
            '_virtual': "yes" if convert['type'] == self.PRODUCT_VIRTUAL else "no",
            '_regular_price': convert['price'],
            '_sale_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                    self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                    convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                'end_date'] == '0000-00-00 00:00:00') or convert['special_price']['end_date'] == '' or
                    convert['special_price']['end_date'] == None) else "",
            '_tax_status': convert['tax'].get('status', (
                "taxable" if to_int(convert['tax']['id']) or convert['tax']['code'] else "none")),
            '_tax_class': tax_class if tax_class else '',
            '_weight': convert['weight'] if convert['weight'] else '',
            '_length': convert['length'] if convert['length'] else '',
            '_width': convert['width'] if convert['width'] else '',
            '_height': convert['height'] if convert['height'] else '',
            '_sku': convert['sku'],
            '_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                    self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                    convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                    convert['special_price']['end_date'] == None)) else convert['price'],
            '_manage_stock': "yes" if convert['manage_stock'] or convert['manage_stock'] == True else "no",
            '_stock': convert['qty'] if convert['qty'] else 0,
            # 'show_on_pos': '1' if convert['pos'] else 0,
        }
        if convert['special_price']['start_date'] and (
                self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
            'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                convert['special_price']['end_date'] == None)):
            product_meta['_sale_price_dates_from'] = self.to_timestamp(convert['special_price']['start_date'])
        if convert['special_price']['end_date'] and (
                self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
            'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                convert['special_price']['end_date'] == None)):
            product_meta['_sale_price_dates_to'] = self.to_timestamp(convert['special_price']['end_date'])
        if 'group_prices' in convert and to_len(convert['group_prices']) > 0:
            product_meta['wholesale_customer_wholesale_price'] = convert['group_prices'][0]['price']
        all_meta_queries = list()
        for meta_key, meta_value in product_meta.items():
            meta_insert = {
                'post_id': product_id,
                'meta_key': meta_key,
                'meta_value': meta_value
            }
            if meta_key == '_sale_price_dates_from' or meta_key == '_sale_price_dates_to':
                query_meta_key = {
                    'type': 'select',
                    'query': "SELECT * FROM `_DBPRF_postmeta` WHERE `post_id` = " + to_str(
                        product_id) + " AND `meta_key` = " + to_str(meta_key) + ""
                }
                check_meta_key = self.select_data_connector(query_meta_key, 'postmeta')
                if (not check_meta_key) or check_meta_key['result'] != 'success' or (not check_meta_key['data']) or (
                        to_len(check_meta_key['data']) == 0):
                    sale_price_data = {
                        'post_id': product_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    meta_price_query = self.create_insert_query_connector("postmeta", sale_price_data)
                    all_query.append(meta_price_query)
            meta_query = self.create_update_query_connector("postmeta", meta_insert,
                                                            {'post_id': product_id, 'meta_key': meta_key})
            all_query.append(meta_query)
        # todo: update children
        children_list = list()
        option_list = list()
        if convert['children']:
            children_list = convert['children']
        else:
            if convert['options']:
                option_list = convert['options']
                if self.count_child_from_option(convert['options']) <= self.VARIANT_LIMIT:
                    children_list = self.convert_option_to_child(option_list, convert)

        if children_list and to_len(children_list) <= self.VARIANT_LIMIT:
            for key_child, product_child in enumerate(children_list):
                children_id = self.get_map_field_by_src(self.TYPE_CHILD, product_child['id'], product_child['code'],
                                                        lang=language_code)
                if not children_id:
                    continue

                if product_child.get('is_in_stock'):
                    child_stock_status = 'instock' if product_child['is_in_stock'] else 'outofstock'
                else:
                    child_stock_status = 'outofstock' if product_child['manage_stock'] else 'instock'
                children_meta = {
                    '_stock_status': child_stock_status,
                    '_sku': product_child['sku'] if product_child['sku'] else '',
                    '_weight': product_child['weight'] if product_child['weight'] else '',
                    '_length': product_child['length'] if product_child['length'] else '',
                    '_width': product_child['width'] if product_child['width'] else '',
                    '_height': product_child['height'] if product_child['height'] else '',
                    '_manage_stock': "yes" if product_child['manage_stock'] else "no",
                    '_stock': product_child['qty'] if product_child['qty'] else 0,
                    '_regular_price': product_child['price'],
                    '_sale_price': product_child['special_price']['price'] if product_child['special_price'][
                                                                                  'price'] and (self.to_timestamp(
                        product_child['special_price']['end_date']) > time.time() or (product_child['special_price'][
                                                                                          'end_date'] == '0000-00-00' or
                                                                                      product_child['special_price'][
                                                                                          'end_date'] == '0000-00-00 00:00:00' or
                                                                                      convert['special_price'][
                                                                                          'end_date'] == '' or
                                                                                      convert['special_price'][
                                                                                          'end_date'] == None)) else
                    product_child['price'],
                    '_price': product_child['special_price']['price'] if product_child['special_price']['price'] and (
                            self.to_timestamp(product_child['special_price']['end_date']) > time.time() or (
                            product_child['special_price']['end_date'] == '0000-00-00' or
                            product_child['special_price']['end_date'] == '0000-00-00 00:00:00' or
                            convert['special_price']['end_date'] == '' or convert['special_price'][
                                'end_date'] == None)) else product_child['price'],
                }
                if product_child['special_price']['price'] and (
                        self.to_timestamp(product_child['special_price']['end_date']) > time.time() or (
                        product_child['special_price']['end_date'] == '0000-00-00' or product_child['special_price'][
                    'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                        convert['special_price']['end_date'] == None)):
                    if product_child['special_price']['start_date']:
                        children_meta['_sale_price_dates_from'] = self.to_timestamp(
                            product_child['special_price']['start_date'])
                    if product_child['special_price']['end_date']:
                        children_meta['_sale_price_dates_to'] = self.to_timestamp(
                            product_child['special_price']['end_date'])

                for meta_key, meta_value in children_meta.items():
                    meta_insert_child = {
                        'post_id': children_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }

                    if meta_key == '_sale_price_dates_from' or meta_key == '_sale_price_dates_to':
                        query_meta_key = {
                            'type': 'select',
                            'query': "SELECT * FROM `_DBPRF_postmeta` WHERE `post_id` = " + to_str(
                                children_id) + " AND `meta_key` = " + to_str(meta_key) + ""
                        }
                        check_meta_key = self.select_data_connector(query_meta_key, 'postmeta')
                        if (not check_meta_key) or check_meta_key['result'] != 'success' or (
                                not check_meta_key['data']) or (to_len(check_meta_key['data']) == 0):
                            sale_price_data = {
                                'post_id': children_id,
                                'meta_key': meta_key,
                                'meta_value': meta_value
                            }
                            meta_price_query = self.create_insert_query_connector("postmeta", sale_price_data)
                            all_query.append(meta_price_query)

                    meta_query_child = self.create_update_query_connector('postmeta', meta_insert_child,
                                                                          {'post_id': children_id,
                                                                           'meta_key': meta_key})
                    all_query.append(meta_query_child)
        # todo: seo
        # begin
        if self.is_exist_lecm_rewrite():
            if (self._notice['config']['seo'] or self._notice['config']['seo_301']) and convert['seo']:
                delete_query = list()
                delete_query.append(
                    self.create_delete_query_connector('lecm_rewrite', {'type': 'product', 'type_id': product_id}))
                self.query_multiple_data_connector(delete_query)
                for seo_url in convert['seo']:
                    if not seo_url['request_path']:
                        continue
                    if old_url_key != seo_url['request_path'].replace(' ', ''):
                        query_check = {
                            'link': seo_url['request_path']
                        }
                        if self.is_wpml() and convert.get('language_code'):
                            query_check['lang'] = convert['language_code']
                        seo_query = {
                            'type': 'select',
                            'query': "SELECT * FROM _DBPRF_lecm_rewrite WHERE " + self.dict_to_where_condition(
                                query_check)
                        }
                        check_seo_exit = self.select_data_connector(seo_query, 'lecm_rewrite')
                        if check_seo_exit and check_seo_exit['result'] == 'success' and to_len(
                                check_seo_exit['data']) > 0:
                            continue
                        else:
                            le_url_rewrite = {
                                'link': to_str(seo_url['request_path']).rstrip('/'),
                                'type': 'product',
                                'type_id': product_id
                            }
                            if self.is_wpml():
                                le_url_rewrite['lang'] = convert.get('language_code')
                            if self._notice['config']['seo_301']:
                                le_url_rewrite['redirect_type'] = 301
                            self.import_data_connector(
                                self.create_insert_query_connector("lecm_rewrite", le_url_rewrite), 'seo_product')

        self.import_multiple_data_connector(all_query, 'update_product')
        if self.is_wpml() and not convert.get('language_code'):
            where_product_wpml = {
                'migration_id': self._migration_id,
                'type': 'product',
            }
            if convert['id']:
                where_product_wpml['id_src'] = convert['id']
            else:
                where_product_wpml['code'] = convert['code']
            product_wpml = self.select_obj(TABLE_MAP, where_product_wpml)
            if product_wpml['result'] == 'success' and product_wpml['data']:
                for product_wpml_row in product_wpml['data']:
                    if product_wpml_row['id_desc'] == product_id or not product_wpml_row.get('lang'):
                        continue
                    convert_wpml = self.get_convert_data_language(convert, target_language_id=language_code)
                    convert_wpml['language_code'] = product_wpml_row['lang']
                    self.update_latest_data_product(product_wpml_row['id_desc'], convert_wpml, product, products_ext)
        return response_success()

    def channel_sync_inventory(self, product_id, convert, product, products_ext, settings={}):
        price_setting = settings.get('price')
        qty_setting = settings.get('qty')
        all_query = list()
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code:
            language_code = self._notice['target']['language_default']
        # Update parent
        product_meta = dict()
        if qty_setting:
            if 'is_in_stock' in convert:
                stock_status = 'instock' if convert['is_in_stock'] else 'outofstock'
            else:
                stock_status = 'outofstock' if convert['manage_stock'] else 'instock'
            product_meta.update({
                '_stock_status': stock_status,
                '_manage_stock': "yes" if convert['manage_stock'] or convert['manage_stock'] == True else "no",
                '_stock': convert['qty'] if convert['qty'] else 0,
            })
        if price_setting:
            product_meta.update({
                '_regular_price': convert['price'],
                '_sale_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                        self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                        convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                    'end_date'] == '0000-00-00 00:00:00') or convert['special_price']['end_date'] == '' or
                        convert['special_price']['end_date'] == None) else "",
                '_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                        self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                        convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                    'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                        convert['special_price']['end_date'] == None)) else convert['price'],
            })
            if convert['special_price']['start_date'] and (
                    self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                    convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                    convert['special_price']['end_date'] == None)):
                product_meta['_sale_price_dates_from'] = self.to_timestamp(convert['special_price']['start_date'])
            if convert['special_price']['end_date'] and (
                    self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                    convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
                'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                    convert['special_price']['end_date'] == None)):
                product_meta['_sale_price_dates_to'] = self.to_timestamp(convert['special_price']['end_date'])
            if 'group_prices' in convert and to_len(convert['group_prices']) > 0:
                product_meta['wholesale_customer_wholesale_price'] = convert['group_prices'][0]['price']
        for meta_key, meta_value in product_meta.items():
            meta_insert = {
                'post_id': product_id,
                'meta_key': meta_key,
                'meta_value': meta_value
            }
            if meta_key == '_sale_price_dates_from' or meta_key == '_sale_price_dates_to':
                query_meta_key = {
                    'type': 'select',
                    'query': "SELECT * FROM `_DBPRF_postmeta` WHERE `post_id` = " + to_str(
                        product_id) + " AND `meta_key` = " + to_str(meta_key) + ""
                }
                check_meta_key = self.select_data_connector(query_meta_key, 'postmeta')
                if (not check_meta_key) or check_meta_key['result'] != 'success' or (not check_meta_key['data']) or (
                        to_len(check_meta_key['data']) == 0):
                    sale_price_data = {
                        'post_id': product_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    meta_price_query = self.create_insert_query_connector("postmeta", sale_price_data)
                    all_query.append(meta_price_query)
            meta_query = self.create_update_query_connector("postmeta", meta_insert,
                                                            {'post_id': product_id, 'meta_key': meta_key})
            all_query.append(meta_query)

        # Update children
        for key_child, product_child in enumerate(convert['children']):
            if self._notice['src']['cart_type'] == 'datasync':
                channel_id = self._notice['src']['config']['api']['channel_id']
                children = get_row_from_list_by_field(product['variants'], 'id', product_child['id'])
                children_id = children['channel'].get(f'channel_{channel_id}', {}).get('product_id')
            else:
                children_id = self.get_map_field_by_src(self.TYPE_CHILD, product_child['id'], product_child['code'],
                                                        lang=language_code)
            if not children_id:
                continue
            children_meta = dict()
            if qty_setting:
                if product_child.get('is_in_stock'):
                    child_stock_status = 'instock' if product_child['is_in_stock'] else 'outofstock'
                else:
                    child_stock_status = 'outofstock' if product_child['manage_stock'] else 'instock'
                children_meta.update({
                    '_stock_status': child_stock_status,
                    '_manage_stock': "yes" if product_child['manage_stock'] else "no",
                    '_stock': product_child['qty'] if product_child['qty'] else 0,
                })
            if price_setting:
                children_meta = {
                    '_regular_price': product_child['price'],
                    '_sale_price': product_child['special_price']['price'] if product_child['special_price'][
                                                                                  'price'] and (self.to_timestamp(
                        product_child['special_price']['end_date']) > time.time() or (product_child['special_price'][
                                                                                          'end_date'] == '0000-00-00' or
                                                                                      product_child['special_price'][
                                                                                          'end_date'] == '0000-00-00 00:00:00' or
                                                                                      convert['special_price'][
                                                                                          'end_date'] == '' or
                                                                                      convert['special_price'][
                                                                                          'end_date'] == None)) else
                    product_child['price'],
                    '_price': product_child['special_price']['price'] if product_child['special_price']['price'] and (
                            self.to_timestamp(product_child['special_price']['end_date']) > time.time() or (
                            product_child['special_price']['end_date'] == '0000-00-00' or
                            product_child['special_price']['end_date'] == '0000-00-00 00:00:00' or
                            convert['special_price']['end_date'] == '' or convert['special_price'][
                                'end_date'] == None)) else product_child['price'],
                }
                if product_child['special_price']['price'] and (
                        self.to_timestamp(product_child['special_price']['end_date']) > time.time() or (
                        product_child['special_price']['end_date'] == '0000-00-00' or product_child['special_price'][
                    'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                        convert['special_price']['end_date'] == None)):
                    if product_child['special_price']['start_date']:
                        children_meta['_sale_price_dates_from'] = self.to_timestamp(
                            product_child['special_price']['start_date'])
                    if product_child['special_price']['end_date']:
                        children_meta['_sale_price_dates_to'] = self.to_timestamp(
                            product_child['special_price']['end_date'])

            for meta_key, meta_value in children_meta.items():
                meta_insert_child = {
                    'post_id': children_id,
                    'meta_key': meta_key,
                    'meta_value': meta_value
                }
                if meta_key == '_sale_price_dates_from' or meta_key == '_sale_price_dates_to':
                    query_meta_key = {
                        'type': 'select',
                        'query': "SELECT * FROM `_DBPRF_postmeta` WHERE `post_id` = " + to_str(
                            children_id) + " AND `meta_key` = " + to_str(meta_key) + ""
                    }
                    check_meta_key = self.select_data_connector(query_meta_key, 'postmeta')
                    if (not check_meta_key) or check_meta_key['result'] != 'success' or (
                            not check_meta_key['data']) or (to_len(check_meta_key['data']) == 0):
                        sale_price_data = {
                            'post_id': children_id,
                            'meta_key': meta_key,
                            'meta_value': meta_value
                        }
                        meta_price_query = self.create_insert_query_connector("postmeta", sale_price_data)
                        all_query.append(meta_price_query)
                meta_query_child = self.create_update_query_connector('postmeta', meta_insert_child,
                                                                      {'post_id': children_id, 'meta_key': meta_key})
                all_query.append(meta_query_child)
        if all_query:
            self.import_multiple_data_connector(all_query, 'sync_inventory')
        return response_success()

    def update_product_after_demo(self, product_id, convert, product, products_ext):
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code:
            language_code = self._notice['target']['language_default']
        all_queries = list()
        query_delete = {
            'type': 'delete',
            'query': 'DELETE FROM _DBPRF_term_relationships WHERE object_id = ' + to_str(
                product_id) + ' AND term_taxonomy_id IN (SELECT term_taxonomy_id FROM _DBPRF_term_taxonomy WHERE taxonomy IN ' + self.list_to_in_condition(
                ['product_brand', 'product_cat']) + ')'
        }
        all_queries.append(query_delete)
        # category
        all_categories = list()
        if convert['categories']:
            for category in convert['categories']:
                category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'],
                                                        language_code)
                if not category_id:
                    category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, None, category['code'], language_code)
                if not category_id:
                    category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], None, language_code)
                if category_id:
                    all_categories.append(category_id)
            all_categories = list(set(all_categories))
            for cate_id in all_categories:
                category_data = {
                    'object_id': product_id,
                    'term_taxonomy_id': cate_id,
                    'term_order': 0
                }
                category_query = self.create_insert_query_connector("term_relationships", category_data)
                all_queries.append(category_query)
        if self._notice['target']['support'][PluginSupport.manufacturers.name]:
            if convert['manufacturer']['id'] or convert['manufacturer']['name']:
                manufacturer_id = self.get_map_field_by_src(self.TYPE_MANUFACTURER, convert['manufacturer']['id'])
                if not manufacturer_id:
                    manufacturer_id = self.get_map_field_by_src(self.TYPE_MANUFACTURER, None,
                                                                convert['manufacturer']['id'])
                if manufacturer_id:
                    relationship_data = {
                        'object_id': product_id,
                        'term_taxonomy_id': manufacturer_id,
                        'term_order': 0
                    }
                    category_query = self.create_insert_query_connector("term_relationships", relationship_data)
                    all_queries.append(category_query)
                elif convert['manufacturer']['name']:
                    slug = self.sanitize_title(convert['manufacturer']['name'])
                    manufacturer_term = {
                        'name': convert['manufacturer']['name'],
                        'slug': slug,
                        'term_group': 0,
                    }
                    manufacturer_term_query = self.create_insert_query_connector('terms', manufacturer_term)
                    term_id = self.import_data_connector(manufacturer_term_query, 'manufacturer')
                    if not term_id:
                        return response_warning('Manufacturer ' + to_str(convert['id']) + ' import false.')
                    manufacturer_taxonomy = {
                        'term_id': term_id,
                        'taxonomy': 'product_brand',
                        'description': '',
                        'parent': 0,
                        'count': 0
                    }
                    manufacturer_taxonomy_query = self.create_insert_query_connector('term_taxonomy',
                                                                                     manufacturer_taxonomy)
                    manufacturer_taxonomy_import = self.import_manufacturer_data_connector(manufacturer_taxonomy_query,
                                                                                           True, convert['id'])

                    if manufacturer_taxonomy_import:
                        relationship_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': manufacturer_id,
                            'term_order': 0
                        }
                        relationship_query = self.create_insert_query_connector("term_relationships", relationship_data)
                        all_queries.append(relationship_query)
                        self.insert_map(self.TYPE_MANUFACTURER, convert['manufacturer']['id'],
                                        manufacturer_taxonomy_import, convert['manufacturer']['name'])

        if convert['tax']['id'] or convert['tax']['code']:
            tax_class = self.get_map_field_by_src(self.TYPE_TAX, convert['tax']['id'], convert['tax']['code'],
                                                  'code_desc')
            if tax_class:
                meta_insert = {
                    'post_id': product_id,
                    'meta_key': '_tax_class',
                    'meta_value': tax_class
                }
                where_meta = {
                    'post_id': product_id,
                    'meta_key': '_tax_class',
                }
                all_queries.append(self.create_update_query_connector('postmeta', meta_insert, where_meta))
        self.import_multiple_data_connector(all_queries, 'update_product')
        return response_success()

    def router_product_import(self, convert, product, products_ext):
        return response_success('product_import')

    def before_product_import(self, convert, product, products_ext):
        return response_success()

    def product_import(self, convert, product, products_ext):
        if not convert['name']:
            return response_error('product ' + to_str(convert['id']) + ' name empty.')
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code or (self.is_polylang() and not language_code):
            language_code = self._notice['target']['language_default']
        code_product = convert['url_key'] if convert['url_key'] and convert['id'] else (
            convert['name'].lower() if convert['name'] else '')
        code_product = code_product.replace('.html', '')
        code_product = self.sanitize_title(code_product).strip('-')
        check_slug_exist = True
        while check_slug_exist:
            check_slug_exist = True if self.select_map(self._migration_id, self.TYPE_PRODUCT, None, None, None,
                                                       code_product) else False
            if check_slug_exist:
                code_product += '-' + to_str(to_int(time.time()))
        guid = self._notice['target']['cart_url'] + "/?product=" + code_product
        product_data = {
            'post_author': 1,
            'post_date': convert['created_at'] if convert['created_at'] else get_current_time(),
            'post_date_gmt': convert['created_at'] if convert['created_at'] else get_current_time(),
            'post_content': self.change_img_src_in_text(get_value_by_key_in_dict(convert, 'description', '')),
            'post_title': self.strip_html_tag(convert['name']),
            'post_excerpt': self.strip_html_tag(get_value_by_key_in_dict(convert, 'short_description', '')),
            'post_status': "publish" if convert['status'] else "draft",
            'comment_status': 'open',
            'ping_status': 'closed',
            'post_password': '',
            'post_name': code_product[:200],
            'to_ping': '',
            'pinged': '',
            'post_modified': convert['updated_at'] if convert['updated_at'] else get_current_time(),
            'post_modified_gmt': convert['updated_at'] if convert['updated_at'] else get_current_time(),
            'post_content_filtered': '',
            'post_parent': 0,
            'guid': guid[:250],
            'menu_order': convert.get('menu_order', 0),
            'post_type': "product",
            'post_mime_type': '',
            'comment_count': 0,
            # 'sort_order': get_value_by_key_in_dict(convert, 'sort_order', 0),
        }
        product_query = self.create_insert_query_connector('posts', product_data)
        product_import = self.import_product_data_connector(product_query, True, convert['id'])
        if not product_import:
            return response_error('Product ' + to_str(convert['id']) + ' import false.')

        sku_product = convert['sku'] if convert['sku'] else ''
        check_sku_exist = True
        if sku_product:
            while check_sku_exist:
                check_sku_exist = True if self.select_map(self._migration_id, self.TYPE_PRODUCT, None, None, None, None,
                                                          sku_product) else False
                if check_sku_exist:
                    sku_product += '-' + to_str(to_int(time.time()))
        convert['sku'] = sku_product

        self.insert_map(self.TYPE_PRODUCT, convert['id'], product_import,
                        convert['code'] if convert['code'] else code_product, code_product, sku_product, language_code)
        # if not self.is_wpml() or (self.is_wpml() and not convert.get('language_code')) and self.is_exist_lecm_rewrite():
        if (self._notice['config']['seo'] or self._notice['config']['seo_301']) and convert['seo']:
            for seo_url in convert['seo']:
                if not seo_url['request_path']:
                    continue
                if code_product != seo_url['request_path'].replace(' ', ''):
                    query_check = {
                        'link': seo_url['request_path']
                    }
                    if self.is_wpml() and convert.get('language_code'):
                        query_check['lang'] = convert['language_code']
                    # else:
                    # 	query_check['lang'] = self._notice['target']['language_default']
                    seo_query = {
                        'type': 'select',
                        'query': "SELECT * FROM _DBPRF_lecm_rewrite WHERE " + self.dict_to_where_condition(query_check)
                    }
                    check_seo_exit = self.select_data_connector(seo_query, 'category')
                    if check_seo_exit and check_seo_exit['result'] == 'success' and check_seo_exit['data']:
                        continue
                    else:
                        le_url_rewrite = {
                            'link': self.parse_url(to_str(seo_url['request_path']).rstrip('/')),
                            'type': 'product',
                            'type_id': product_import,
                        }
                        if self.is_wpml():
                            le_url_rewrite['lang'] = convert.get('language_code')
                        if self._notice['config']['seo_301']:
                            le_url_rewrite['redirect_type'] = 301
                        self.import_data_connector(self.create_insert_query_connector("lecm_rewrite", le_url_rewrite),
                                                   'seo_product')
        if self.is_wpml():
            self.rf_process_image_wpml(convert)
        return response_success(product_import)

    def rf_process_image_wpml(self, convert):

        config_image_path = self._notice['target']['config']['image_product'].rstrip('/') if not self._notice['target'][
            'config'].get('site_id') else self._notice['target']['config']['image_product'].rstrip(
            '/') + '/sites/' + to_str(self._notice['target']['config']['site_id'])
        if convert['thumb_image']['url'] or convert['thumb_image']['path']:
            image_process = self.process_image_before_import(convert['thumb_image']['url'],
                                                             convert['thumb_image']['path'])
            rf_path = self.get_map_field_by_src(self.TYPE_PATH_IMAGE, None, image_process['url'], field='code_desc')
            if not rf_path:
                image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                self.make_woocommerce_image_path(image_process['path']), config_image_path))

                if image_import_path:
                    product_image = self.remove_prefix_path(image_import_path,
                                                            self._notice['target']['config']['image_product'])
                    _, image_details = self.get_sizes(image_process['url'])
                    # wp_image(self, path, image_details = None, label = '', convert = dict, check_exist=True)
                    trid = self.get_new_trid()
                    for lang_code, lang_name in self._notice['target']['languages'].items():
                        thumbnail_id = self.wp_image(product_image, image_details, convert['thumb_image'].get('label', ''),
                                                     check_exist=False, lang=lang_code)
                        if thumbnail_id and self.is_wpml():
                            res = self.import_data_connector(self.rf_get_query_img_wpml(thumbnail_id, lang_code, trid))
        if convert['images']:
            for image in convert['images']:
                image_process = self.process_image_before_import(image['url'], image['path'])
                rf_path = self.get_map_field_by_src(self.TYPE_PATH_IMAGE, None, image_process['url'], field='code_desc')
                if rf_path:
                    continue
                image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                    self.make_woocommerce_image_path(image_process['path']), config_image_path))
                if image_import_path:
                    product_image = self.remove_prefix_path(image_import_path,
                                                            self._notice['target']['config']['image_product'])
                    _, image_details = self.get_sizes(image_process['url'])
                    trid = self.get_new_trid()
                    for lang_code, lang_name in self._notice['target']['languages'].items():
                        img_id = self.wp_image(product_image, image_details, image['label'],
                                               check_exist=False, lang=lang_code)
                        if img_id and self.is_wpml():
                            res = self.import_data_connector(self.rf_get_query_img_wpml(img_id, lang_code, trid))

    def rf_get_map_by_field_language(self, map_type=None, id_src=None, code_src=None, lang=None, field='id_desc'):
        if not id_src and not code_src:
            return False
        map_data = self.select_raw(f"Select * from `migration_map` where type = '{map_type}' and lang = '{lang}' "
                                   f"and code_src = {self.escape(code_src)}")
        if map_data.get('result') != 'success':
            return False
        if map_data.get('data') and map_data['data']:
            return map_data['data'][0].get(field)

    def after_product_import(self, product_id, convert, product, products_ext):
        language_code = convert.get('language_code')
        product_type = 'simple'
        if self.is_wpml() and not language_code or (self.is_polylang() and not language_code):
            language_code = self._notice['target']['language_default']
        all_queries = list()
        thumbnail_id = False
        gallery_meta_value = ''
        if self.is_wpml():
            if convert['thumb_image']['url'] or convert['thumb_image']['path']:
                image_process = self.process_image_before_import(convert['thumb_image']['url'],
                                                                 convert['thumb_image']['path'])
                rf_path = self.get_map_field_by_src(self.TYPE_PATH_IMAGE, None, image_process['url'], field='code_desc')
                if rf_path:
                    rf_url = self._notice['target']['cart_url'].rstrip('/') + '/' + rf_path.lstrip('/')
                    thumbnail_id = self.rf_get_map_by_field_language(map_type='wp_image', id_src=None, code_src=rf_url,
                                                                     lang=language_code)
            gallery_ids = list()
            if convert['images']:
                for image in convert['images']:
                    image_process = self.process_image_before_import(image['url'], image['path'])
                    rf_path = self.get_map_field_by_src(self.TYPE_PATH_IMAGE, None, image_process['url'],
                                                        field='code_desc')
                    if rf_path:
                        rf_url = self._notice['target']['cart_url'].rstrip('/') + '/' + rf_path.lstrip('/')
                        img_id = self.rf_get_map_by_field_language(map_type='wp_image', id_src=None, code_src=rf_url,
                                                                    lang=language_code)
                        if img_id and not thumbnail_id:
                            thumbnail_id = copy.deepcopy(img_id)
                            continue
                        gallery_ids.append(img_id)
            gallery_meta_value = ','.join(str(id) for id in gallery_ids)
        else:
            config_image_path = self._notice['target']['config']['image_product'].rstrip('/') if not self._notice['target'][
                'config'].get('site_id') else self._notice['target']['config']['image_product'].rstrip(
                '/') + '/sites/' + to_str(self._notice['target']['config']['site_id'])
            if convert['thumb_image']['url'] or convert['thumb_image']['path']:
                image_process = self.process_image_before_import(convert['thumb_image']['url'],
                                                                 convert['thumb_image']['path'])
                image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                    self.make_woocommerce_image_path(image_process['path']), config_image_path))

                if image_import_path:
                    product_image = self.remove_prefix_path(image_import_path,
                                                            self._notice['target']['config']['image_product'])
                    _, image_details = self.get_sizes(image_process['url'])
                    thumbnail_id = self.wp_image(product_image, image_details, convert['thumb_image'].get('label', ''))
                    if thumbnail_id and self.is_wpml():
                        all_queries.append(self.get_query_img_wpml(thumbnail_id, language_code))

            # gallery product
            gallery_ids = list()
            if convert['images']:
                for image in convert['images']:
                    image_process = self.process_image_before_import(image['url'], image['path'])
                    image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                        self.make_woocommerce_image_path(image_process['path']), config_image_path))
                    if image_import_path:
                        product_image = self.remove_prefix_path(image_import_path,
                                                                self._notice['target']['config']['image_product'])
                        _, image_details = self.get_sizes(image_process['url'])
                        img_id = self.wp_image(product_image, image_details, image['label'])
                        if img_id:
                            gallery_ids.append(img_id)
                            if self.is_wpml():
                                all_queries.append(self.get_query_img_wpml(img_id, language_code))

            gallery_meta_value = ','.join(str(id) for id in gallery_ids)
        upsell_ids = list()
        crosssell_ids = list()
        if convert['relate']['children']:
            for relate_src in convert['relate']['children']:
                relate_desc_id = self.get_map_field_by_src(self.TYPE_PRODUCT, relate_src['id'], relate_src['code'],
                                                           language_code)
                if not relate_desc_id:
                    relate_desc_id = self.get_map_field_by_src(self.TYPE_PRODUCT, None, relate_src['code'],
                                                               language_code)
                if relate_desc_id:
                    if relate_src['type'] == self.PRODUCT_RELATE or relate_src['type'] == self.PRODUCT_CROSS:
                        crosssell_ids.append(relate_desc_id)
                    else:
                        upsell_ids.append(relate_desc_id)
        downloadable_files = {}
        download_expiry = -1
        download_limit = -1
        if convert['type'] == self.PRODUCT_DOWNLOAD and convert.get('downloadable'):
            i = 0
            for download_data in convert['downloadable']:
                if to_int(download_data.get('max_day')) > 0:
                    download_expiry = to_int(download_data.get('max_day'))
                if to_int(download_data.get('limit')) > 0:
                    download_limit = to_int(download_data.get('limit'))
                i = i + 1
                id_download = to_str(product_id) + '-' + to_str(i)
                download_item = {
                    'id': id_download,
                    'name': download_data.get('name'),
                    'file': self._notice['target']['cart_url'] + "/wp-content/uploads/downloadable/" + to_str(
                        download_data.get('path')).strip('/'),
                }
                downloadable_files[id_download] = download_item

        if convert['relate']['parent']:
            for upsell_src in convert['relate']['parent']:
                parent_desc_id = self.get_map_field_by_src(self.TYPE_PRODUCT, upsell_src['id'], upsell_src['code'],
                                                           language_code)
                if not parent_desc_id:
                    parent_desc_id = self.get_map_field_by_src(self.TYPE_PRODUCT, None, upsell_src['code'],
                                                               language_code)
                if parent_desc_id:
                    if (upsell_src['type'] == self.PRODUCT_RELATE) or (upsell_src['type'] == self.PRODUCT_UPSELL):
                        query = {
                            'type': 'select',
                            'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id = " + to_str(
                                parent_desc_id) + "  AND meta_key = '_upsell_ids'"
                        }
                        parent_meta_upsell = self.get_connector_data(self.get_connector_url('query'),
                                                                     {'query': json.dumps(query)})
                        if not parent_meta_upsell or parent_meta_upsell['result'] != 'success':
                            continue
                        if parent_meta_upsell['data']:
                            old_value = parent_meta_upsell['data'][0]['meta_value']
                            new_value = php_unserialize(old_value) if old_value else list()
                            if isinstance(new_value, dict):
                                new_value[to_len(new_value)] = product_id
                            else:
                                new_value.append(product_id)
                            new_query = "UPDATE _DBPRF_postmeta set meta_value = '" + php_serialize(
                                new_value) + "' WHERE post_id = " + to_str(
                                parent_desc_id) + " AND meta_key = '_upsell_ids'"
                            all_queries.append({
                                'type': 'query',
                                'query': new_query
                            })
                    else:
                        query = {
                            'type': 'select',
                            'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id = " + to_str(
                                parent_desc_id) + "  AND meta_key = '_crosssell_ids'"
                        }
                        parent_meta_crosssell = self.get_connector_data(self.get_connector_url('query'),
                                                                        {'query': json.dumps(query)})
                        if not parent_meta_crosssell or parent_meta_crosssell['result'] != 'success':
                            continue
                        if parent_meta_crosssell['data']:
                            old_value = parent_meta_crosssell['data'][0]['meta_value']
                            new_value = php_unserialize(old_value) if old_value else list()
                            if isinstance(new_value, dict):
                                new_value[to_len(new_value)] = product_id
                            else:
                                new_value.append(product_id)
                            new_query = "UPDATE _DBPRF_postmeta set meta_value = '" + php_serialize(
                                new_value) + "' WHERE post_id = " + to_str(
                                parent_desc_id) + " AND meta_key = '_crosssell_ids'"
                            all_queries.append({
                                'type': 'query',
                                'query': new_query
                            })
        tax_class = ''
        if convert['tax']['id'] or convert['tax']['code']:
            tax_class = self.get_map_field_by_src(self.TYPE_TAX, convert['tax']['id'], convert['tax']['code'],
                                                  field='code_desc')

        # product_meta
        stock_status = 'instock'
        if convert.get('is_in_stock'):
            stock_status = 'instock' if convert['is_in_stock'] else 'outofstock'
        else:
            stock_status = 'outofstock' if convert['manage_stock'] else 'instock'

        if self.is_woo2woo():
            stock_status = convert.get('is_in_stock', 'instock')

        product_meta = {
            '_product_attributes': php_serialize(list()),
            '_thumbnail_id': thumbnail_id if thumbnail_id else "",
            '_visibility': "visible",
            '_stock_status': stock_status,
            'total_sales': 0,
            '_downloadable': "yes" if convert['type'] == self.PRODUCT_DOWNLOAD else "no",
            '_download_limit': download_limit,
            '_download_expiry': download_expiry,
            '_virtual': "yes" if convert['type'] == self.PRODUCT_VIRTUAL else "no",
            '_regular_price': convert['price'],
            '_sale_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                    to_int(self.to_timestamp(convert['special_price']['end_date'])) > to_int(time.time()) or
                    convert['special_price']['end_date'] == '' or convert['special_price'][
                        'end_date'] == '0000-00-00' or convert['special_price'][
                        'end_date'] == '0000-00-00 00:00:00' or convert['special_price'][
                        'end_date'] == None) else "",
            '_tax_status': convert['tax'].get('status', (
                "taxable" if to_int(convert['tax']['id']) or convert['tax']['code'] else "none")),
            '_tax_class': tax_class if tax_class else '',
            '_featured': "no",
            '_purchase_note': convert.get('purchase_note', ''),
            '_weight': convert['weight'] if convert['weight'] else '',
            '_length': convert['length'] if convert['length'] else '',
            '_width': convert['width'] if convert['width'] else '',
            '_height': convert['height'] if convert['height'] else '',
            '_sku': convert['sku'],
            '_price': convert['special_price']['price'] if convert['special_price']['price'] and (
                    to_int(self.to_timestamp(convert['special_price']['end_date'])) > to_int(time.time()) or
                    convert['special_price']['end_date'] == '' or convert['special_price'][
                        'end_date'] == '0000-00-00' or convert['special_price'][
                        'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == None) else
            convert['price'],
            '_sold_individually': convert.get('sold_individually', ''),
            '_manage_stock': "yes" if convert['manage_stock'] or convert['manage_stock'] == True else "no",
            '_backorders': convert.get('backorders', 'no'),
            '_stock': convert['qty'] if convert['qty'] else 0,
            '_upsell_ids': php_serialize(upsell_ids),
            '_crosssell_ids': php_serialize(crosssell_ids),
            '_min_variation_price': "",
            '_max_variation_price': "",
            '_min_price_variation_id': "",
            '_max_price_variation_id': "",
            '_min_variation_regular_price': "",
            '_max_variation_regular_price': "",
            '_min_regular_price_variation_id': "",
            '_max_regular_price_variation_id': "",
            '_min_variation_sale_price': "",
            '_max_variation_sale_price': "",
            '_min_sale_price_variation_id': "",
            '_max_sale_price_variation_id': "",
            '_default_attributes': php_serialize(list()),
            '_product_image_gallery': gallery_meta_value,
            '_downloadable_files': php_serialize(downloadable_files),
            '_wc_review_count': 0,
            '_wc_average_rating': 0
        }
        if not product_meta['_price'] or to_decimal(product_meta['_price']) == 0:
            product_meta['_price'] = product_meta['_regular_price']
        if 'group_prices' in convert and to_len(convert['group_prices']) > 0:
            product_meta['wholesale_customer_wholesale_price'] = convert['group_prices'][0]['price']
        if convert['special_price']['start_date'] and (
                self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
            'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                convert['special_price']['end_date'] == None)):
            product_meta['_sale_price_dates_from'] = self.to_timestamp(convert['special_price']['start_date'])
        if convert['special_price']['end_date'] and (
                self.to_timestamp(convert['special_price']['end_date']) > time.time() or (
                convert['special_price']['end_date'] == '0000-00-00' or convert['special_price'][
            'end_date'] == '0000-00-00 00:00:00' or convert['special_price']['end_date'] == '' or
                convert['special_price']['end_date'] == None)):
            product_meta['_sale_price_dates_to'] = self.to_timestamp(convert['special_price']['end_date'])
        # if self._notice['target']['support']['yoast_seo']:
        product_meta['_yoast_wpseo_title'] = to_str(convert['meta_title']).replace('%',
                                                                                   '') if 'meta_title' in convert and \
                                                                                          convert['meta_title'] else ''
        product_meta['_yoast_wpseo_metadesc'] = to_str(convert['meta_description']).replace('%',
                                                                                            '') if 'meta_description' in convert and \
                                                                                                   convert[
                                                                                                       'meta_description'] else ''

        # product bundle plugin: WPC Product Bundles for WooCommerce (Premium)
        if self._notice['target']['support']['product_bundle'] and convert['type'] == self.PRODUCT_BUNDLE:
            product_meta['woosb_ids'] = ''
            if 'bundle_selection' in convert and convert['bundle_selection']:
                for bundle_selection in convert['bundle_selection']:
                    child_bundle_id = self.get_map_field_by_src(self.TYPE_PRODUCT, bundle_selection['product_id'], None,
                                                                self._notice['target']['language_default'])
                    if not child_bundle_id:
                        continue
                    if product_meta['woosb_ids'] == '':
                        product_meta['woosb_ids'] = to_str(child_bundle_id) + '/' + to_str(
                            to_int(to_decimal(bundle_selection['selection_qty'])))
                    else:
                        product_meta['woosb_ids'] = to_str(product_meta['woosb_ids']) + ',' + to_str(
                            child_bundle_id) + '/' + to_str(to_int(to_decimal(bundle_selection['selection_qty'])))
            product_meta['woosb_disable_auto_price'] = 'on'
            product_meta['woosb_discount'] = 0
            product_meta['woosb_discount_amount'] = ''
            product_meta['woosb_shipping_fee'] = 'whole'
            product_meta['woosb_optional_products'] = 'off'
            product_meta['woosb_limit_each_min'] = ''
            product_meta['woosb_limit_each_max'] = ''
            product_meta['woosb_limit_each_min_default'] = 'off'
            product_meta['woosb_limit_whole_min'] = ''
            product_meta['woosb_limit_whole_max'] = ''

        # product mutil currency
        if self._notice['target']['support'].get('wpml_currency'):
            product_meta['_wcml_custom_prices_status'] = 1
            for language, data_language in convert['languages'].items():
                if 'price' not in data_language:
                    continue
                language_target = self._notice['map']['languages'].get(language)
                if not language_target:
                    language_target = self._notice['map']['languages'].get(to_int(language))
                if not language_target or to_str(language_target) == to_str(language_code):
                    continue
                lang_currency_switch = self._notice['target']['currency_map'].get(to_str(language_target))
                if not lang_currency_switch:
                    continue
                product_meta['_regular_price_' + to_str(lang_currency_switch)] = data_language['price']
                product_meta['_wcml_schedule_' + to_str(lang_currency_switch)] = 0
                product_meta['_sale_price_dates_from_' + to_str(lang_currency_switch)] = None
                product_meta['_price_' + to_str(lang_currency_switch)] = data_language['price']

        # custom description yikes_woo_products_tabs

        # if 'custom_desc' in convert:
        # 	desc_list = list()
        # 	list_image_desc = list()
        # 	for description, content in convert['custom_desc'].items():
        # 		desc_dict = dict()
        # 		desc_dict['title'] = description
        # 		desc_dict['id'] = description.replace(' ', '-')
        # 		desc_dict['content'] = content
        # 		desc_list.append(desc_dict)
        # 	product_meta['yikes_woo_products_tabs'] = php_serialize(desc_list)

        all_meta_queries = list()
        for meta_key, meta_value in product_meta.items():
            meta_insert = {
                'post_id': product_id,
                'meta_key': meta_key,
                'meta_value': meta_value
            }
            meta_query = self.create_insert_query_connector("postmeta", meta_insert)
            all_meta_queries.append(meta_query)
        if all_meta_queries:
            self.import_multiple_data_connector(all_meta_queries, 'products')
            all_meta_queries = list()

        product_meta_lookup = {
            'product_id': product_id,
            'sku': convert['sku'],
            'virtual': 1 if convert['type'] == self.PRODUCT_VIRTUAL else 0,
            'downloadable': 1 if convert['type'] == self.PRODUCT_DOWNLOAD else 0,
            'min_price': product_meta['_price'],
            'max_price': product_meta['_price'],
            'onsale': 0,
            'stock_quantity': convert['qty'] if convert['qty'] else 0,
            'stock_status': stock_status,
            'rating_count': 0,
            'average_rating': 0.00,
            'total_sales': 0,
        }
        all_queries.append(self.create_insert_query_connector('wc_product_meta_lookup', product_meta_lookup))
        # self.import_product_data_connector(product_meta_lookup_query, True, convert['id'])

        # todo: plugin add-ons

        # feature field
        if convert.get('feature_field', False):
            for feature_item in convert['feature_field']:
                product_meta_field_data = {
                    'post_id': product_id,
                    'meta_key': feature_item['name'],
                    'meta_value': feature_item['value'],
                }
                product_meta_field_query = self.create_insert_query_connector("postmeta", product_meta_field_data)
                all_meta_queries.append(product_meta_field_query)
        if all_meta_queries:
            self.import_multiple_data_connector(all_meta_queries, 'products')
            all_meta_queries = list()
        # category
        all_categories = list()
        if convert['categories']:
            for category in convert['categories']:
                category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], category['code'],
                                                        language_code)
                if not category_id:
                    category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, None, category['code'], language_code)
                if not category_id:
                    category_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category['id'], None, language_code)
                if category_id:
                    all_categories.append(category_id)
            all_categories = list(set(all_categories))
            for cate_id in all_categories:
                category_data = {
                    'object_id': product_id,
                    'term_taxonomy_id': cate_id,
                    'term_order': 0
                }
                category_query = self.create_insert_query_connector("term_relationships", category_data)
                all_queries.append(category_query)
        if self._notice['target']['support']['manufacturers']:
            if convert['manufacturer']['id'] or convert['manufacturer']['name']:
                manufacturer_id = self.get_map_field_by_src(self.TYPE_MANUFACTURER, convert['manufacturer']['id'],
                                                            convert['manufacturer']['code'])
                # if not manufacturer_id:
                # 	manufacturer_id = self.get_map_field_by_src(self.TYPE_MANUFACTURER, None, convert['manufacturer']['id'])
                if manufacturer_id:
                    relationship_data = {
                        'object_id': product_id,
                        'term_taxonomy_id': manufacturer_id,
                        'term_order': 0
                    }
                    category_query = self.create_insert_query_connector("term_relationships", relationship_data)
                    all_queries.append(category_query)
                elif convert['manufacturer']['name']:
                    slug = self.sanitize_title(convert['manufacturer']['name'])
                    manufacturer_term = {
                        'name': convert['manufacturer']['name'],
                        'slug': slug,
                        'term_group': 0,
                    }
                    manufacturer_term_query = self.create_insert_query_connector('terms', manufacturer_term)
                    term_id = self.import_data_connector(manufacturer_term_query, 'manufacturer')
                    if not term_id:
                        return response_warning('Manufacturer ' + to_str(convert['id']) + ' import false.')
                    manufacturer_taxonomy = {
                        'term_id': term_id,
                        'taxonomy': 'product_brand',
                        'description': '',
                        'parent': 0,
                        'count': 0
                    }
                    manufacturer_taxonomy_query = self.create_insert_query_connector('term_taxonomy',
                                                                                     manufacturer_taxonomy)
                    manufacturer_taxonomy_import = self.import_manufacturer_data_connector(manufacturer_taxonomy_query,
                                                                                           True, convert['id'])

                    if manufacturer_taxonomy_import:
                        relationship_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': manufacturer_taxonomy_import,
                            'term_order': 0
                        }
                        relationship_query = self.create_insert_query_connector("term_relationships", relationship_data)
                        all_queries.append(relationship_query)
                        self.insert_map(self.TYPE_MANUFACTURER, convert['manufacturer']['id'],
                                        manufacturer_taxonomy_import, convert['manufacturer']['name'])

        # TODO: featured
        if convert.get('is_featured'):
            featured = self.get_connector_data(self.get_connector_url('query'), {
                'query': json.dumps({
                    'type': 'select',
                    'query': "SELECT * FROM _DBPRF_terms WHERE slug = 'featured'",
                })
            })
            if featured and featured['data']:
                feature_id = featured['data'][0]['term_id']
                if feature_id:
                    feature_data = {
                        'object_id': product_id,
                        'term_taxonomy_id': feature_id,
                        'term_order': 0
                    }
                    category_query = self.create_insert_query_connector("term_relationships", feature_data)
                    all_queries.append(category_query)
        # end: featured

        if convert['tags']:
            tags_src = convert['tags'].split(',')
            if tags_src:
                check_exist_term_query = {
                    # 'terms': {
                    # 	'type': 'select',
                    # 	'query': "SELECT * FROM _DBPRF_terms WHERE name IN " + self.list_to_in_condition(tags_src)
                    # },
                    'product_tag': {
                        'type': 'select',
                        'query': "SELECT * FROM _DBPRF_terms AS t JOIN _DBPRF_term_taxonomy As tt ON t.term_id = tt.term_id WHERE tt.taxonomy = 'product_tag' AND t.name IN " + self.list_to_in_condition(
                            tags_src)
                    }
                }
                check_exist_term = self.select_multiple_data_connector(check_exist_term_query)
                # check_exist_term_data = dict()
                check_exist_tag_data = dict()
                if check_exist_term['result'] == 'success' and check_exist_term['data']:
                    if check_exist_term['data']['product_tag']:
                        for check_exist_tag_row in check_exist_term['data']['product_tag']:
                            check_exist_tag_data[check_exist_tag_row['name']] = check_exist_tag_row['term_taxonomy_id']
                # if check_exist_term['data']['terms']:
                # 	for check_exist_term_row in check_exist_term['data']['terms']:
                # 		check_exist_term_data[check_exist_term_row['name']] = check_exist_term_row['term_id']
                for tag_src in tags_src:
                    if tag_src in check_exist_tag_data:
                        tag_id = check_exist_tag_data[tag_src]
                    else:
                        # if tag_src in check_exist_term_data:
                        # 	term_value_id = check_exist_term_data[tag_src]
                        # else:
                        value_term = {
                            'name': tag_src,
                            'slug': self.sanitize_title(tag_src),
                            'term_group': 0,
                        }
                        value_term_query = self.create_insert_query_connector('terms', value_term)
                        term_value_id = self.import_data_connector(value_term_query, 'products')
                        # check_exist_term_data[tag_src] = term_value_id
                        if not term_value_id:
                            continue

                        value_term_taxonomy = {
                            'term_id': term_value_id,
                            'taxonomy': "product_tag",
                            'description': tag_src,
                            'parent': 0,
                            'count': 0
                        }
                        tag_id = self.import_data_connector(
                            self.create_insert_query_connector('term_taxonomy', value_term_taxonomy), 'products')
                        check_exist_tag_data[tag_src] = tag_id

                    if tag_id:
                        relationship = {
                            'object_id': product_id,
                            'term_taxonomy_id': tag_id,
                            'term_order': 0
                        }
                        all_queries.append(self.create_insert_query_connector('term_relationships', relationship))
        # product type

        pro_attr = dict()
        if convert['attributes']:
            position = 0
            for option in convert['attributes']:
                if option['option_value_name'] and option['option_value_name'] != '':
                    pro_attr_code = self.get_pro_attr_code_default(option)
                    if (to_int(option.get('is_taxonomy')) == 1 or option['option_id'] or not self.is_woo2woo()) and \
                            option['option_type'] != 'text':
                        woo_attribute_id = self.get_woo_attribute_id(pro_attr_code, option['option_name'],
                                                                     language_code, option)
                        if not woo_attribute_id:
                            values = option['option_value_name']
                            if isinstance(values, list):
                                attribute_product = ' | '.join(values)
                            else:
                                attribute_product = values
                            pro_attr[pro_attr_code] = {
                                'name': option['option_name'],
                                'value': attribute_product,
                                'position': position,
                                'is_visible': 0 if ('is_visible' in option) and (not option['is_visible']) else 1,
                                'is_variation': 1 if option.get('is_variation') else 0,
                                'is_taxonomy': 0
                            }
                            position += 1
                            continue

                        if option['option_value_name']:
                            option_value = option['option_value_name']
                            descs = get_value_by_key_in_dict(option, 'option_value_description', '')
                            if option['option_type'] == self.OPTION_MULTISELECT:
                                option_value_list = to_str(option_value).split(';')
                                desc_value_list = descs.split(';')
                                for key_op, option_value_child in enumerate(option_value_list):
                                    new_option = copy.deepcopy(option)
                                    new_option['option_value_name'] = option_value_child
                                    new_option['position_option'] = key_op
                                    desc_value_child = ''
                                    for nk_op, desc_child in enumerate(desc_value_list):
                                        if to_str(nk_op) == to_str(key_op):
                                            desc_value_child = desc_child
                                    opt_value_id = self.get_woo_attribute_value(option_value_child, pro_attr_code,
                                                                                language_code, new_option,
                                                                                desc_value_child)
                                    if not opt_value_id:
                                        continue
                                    where_count_update = {
                                        'term_taxonomy_id': opt_value_id,
                                    }
                                    query_update = {
                                        'type': 'update',
                                        'query': "UPDATE _DBPRF_term_taxonomy SET `count` = `count` + 1 WHERE " + self.dict_to_where_condition(
                                            where_count_update)
                                    }
                                    self.import_data_connector(query_update, 'products')

                                    relationship = {
                                        'object_id': product_id,
                                        'term_taxonomy_id': opt_value_id,
                                        'term_order': 0
                                    }
                                    all_queries.append(
                                        self.create_insert_query_connector('term_relationships', relationship))
                            else:
                                opt_value_id = self.get_woo_attribute_value(option_value, pro_attr_code, language_code,
                                                                            option, descs)
                                if not opt_value_id:
                                    continue
                                where_count_update = {
                                    'term_taxonomy_id': opt_value_id,
                                }
                                query_update = {
                                    'type': 'update',
                                    'query': "UPDATE _DBPRF_term_taxonomy SET `count` = `count` + 1 WHERE " + self.dict_to_where_condition(
                                        where_count_update)
                                }
                                self.import_data_connector(query_update, 'products')

                                relationship = {
                                    'object_id': product_id,
                                    'term_taxonomy_id': opt_value_id,
                                    'term_order': 0
                                }
                                all_queries.append(
                                    self.create_insert_query_connector('term_relationships', relationship))

                        pro_attr["pa_" + pro_attr_code] = {
                            'name': "pa_" + urllib.parse.unquote_plus(pro_attr_code),
                            'value': '',
                            'position': position,
                            'is_visible': 0 if ('is_visible' in option) and (not option['is_visible']) else 1,
                            'is_variation': 1 if option.get('is_variation') else 0,
                            'is_taxonomy': 1
                        }
                        position += 1
                    else:
                        values = option['option_value_name']
                        if option['option_type'] == self.OPTION_MULTISELECT:
                            list_value = to_str(values).split(';')
                            values = ' | '.join(list_value)
                        attribute_product = values
                        pro_attr[pro_attr_code] = {
                            'name': option['option_name'],
                            'value': attribute_product,
                            'position': position,
                            'is_visible': 0 if ('is_visible' in option) and (not option['is_visible']) else 1,
                            'is_variation': 1 if option.get('is_variation') else 0,
                            'is_taxonomy': 0
                        }
                        position += 1
        if self.get_migrate_product_extend_config():
            # todo: group product
            if convert['group_parent_ids']:
                for parent in convert['group_parent_ids']:
                    parent_id_import = self.get_map_field_by_src(self.TYPE_PRODUCT, parent['id'], lang=language_code)
                    if parent_id_import:
                        query = {
                            'type': 'select',
                            'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id = " + to_str(
                                parent_id_import) + "  AND meta_key = '_children'"
                        }
                        parent_meta_children = self.get_connector_data(self.get_connector_url('query'),
                                                                       {'query': json.dumps(query)})
                        if not parent_meta_children or parent_meta_children['result'] != 'success':
                            continue
                        if parent_meta_children['data']:
                            old_value = parent_meta_children['data'][0]['meta_value']
                            new_value = php_unserialize(old_value) if old_value else list()
                            if isinstance(new_value, dict):
                                new_value = list(new_value.values())
                            new_value.append(product_id)
                            new_query = "UPDATE _DBPRF_postmeta set meta_value = '" + php_serialize(
                                new_value) + "' WHERE post_id = " + to_str(
                                parent_id_import) + " AND meta_key = '_children'"
                            all_queries.append({
                                'type': 'query',
                                'query': new_query
                            })
                        else:
                            new_value = list()
                            new_value.append(product_id)
                            new_query = "INSERT INTO _DBPRF_postmeta (post_id, meta_key, meta_value) VALUES ( " + to_str(
                                parent_id_import) + ", '_children', '" + php_serialize(new_value) + "')"
                            all_queries.append({
                                'type': 'query',
                                'query': new_query
                            })

            if convert['type'] == self.PRODUCT_GROUP:
                product_type = 'grouped'
                if convert.get('group_child_ids'):
                    list_childs = list()
                    for child in convert['group_child_ids']:
                        child_id_import = self.get_map_field_by_src(self.TYPE_PRODUCT, child['id'], lang=language_code)
                        if child_id_import:
                            list_childs.append(child_id_import)
                    meta_insert = {
                        'post_id': product_id,
                        'meta_key': '_children',
                        'meta_value': php_serialize(list_childs)
                    }
                    meta_query = self.create_insert_query_connector("postmeta", meta_insert)
                    all_queries.append(meta_query)

            # todo: variable product
            children_list = list()
            option_list = list()
            if convert['children']:
                children_list = convert['children']
                if to_len(children_list) > 100:
                    msg = 'Product '
                    if convert['id']:
                        msg += 'id ' + to_str(convert['id'])
                    elif convert['code']:
                        msg += 'code: ' + convert['code']
                    msg += ": too much variant (" + to_str(to_len(children_list)) + ")"
                    self.log(msg, 'variant')
                option_list = self.convert_child_to_option(children_list)
            else:
                if convert['options']:
                    option_list = convert['options']
                    if self.count_child_from_option(convert['options']) <= self.VARIANT_LIMIT:
                        children_list = self.convert_option_to_child(option_list, convert)
            if children_list and option_list and not self._notice['target']['support'].get('addons') and to_len(
                    children_list) <= self.VARIANT_LIMIT:
                # Del option_type = Text
                for option in option_list:
                    if option['option_type'] == self.OPTION_TEXT or option['option_type'] == 'file':
                        option_list.remove(option)
                product_type = 'variable'
            if convert['type'] == self.PRODUCT_BUNDLE:
                product_type = 'woosb'
            if convert['type'] == self.PRODUCT_CONFIG and self.is_woo2woo():
                product_type = 'variable'
            taxonomy_id = self.get_product_type(product_type)
            type_data = {
                'object_id': product_id,
                'term_taxonomy_id': taxonomy_id,
                'term_order': 0
            }
            type_query = self.create_insert_query_connector("term_relationships", type_data)
            all_queries.append(type_query)
            if 'visibility' in convert:
                term_not_search_id = self.get_term_by_name('exclude-from-search')
                term_not_catalog_id = self.get_term_by_name('exclude-from-catalog')
                if term_not_search_id and term_not_catalog_id:
                    if convert.get('visibility') == 'not':
                        type_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': term_not_search_id,
                            'term_order': 0
                        }
                        type_query = self.create_insert_query_connector("term_relationships", type_data)
                        all_queries.append(type_query)
                        type_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': term_not_catalog_id,
                            'term_order': 0
                        }
                        type_query = self.create_insert_query_connector("term_relationships", type_data)
                        all_queries.append(type_query)
                    elif convert.get('visibility') == 'search':
                        type_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': term_not_catalog_id,
                            'term_order': 0
                        }
                        type_query = self.create_insert_query_connector("term_relationships", type_data)
                        all_queries.append(type_query)
                    elif convert.get('visibility') == 'catalog':
                        type_data = {
                            'object_id': product_id,
                            'term_taxonomy_id': term_not_search_id,
                            'term_order': 0
                        }
                        type_query = self.create_insert_query_connector("term_relationships", type_data)
                        all_queries.append(type_query)

            if self._notice['target']['support']['addons'] and not self.is_woo2woo():
                meta_addons = list()
                for option in option_list:
                    option_data = option
                    type = option['option_type'].lower()
                    option_type = 'multiple_choice'
                    if type.find('text') >= 0:
                        option_type = 'custom_text'
                    elif type.find('area') >= 0:
                        option_type = 'custom_textarea'
                    elif type.find('checkbox') >= 0:
                        option_type = 'checkbox'
                    elif type.find('file') >= 0:
                        option_type = 'file_upload'
                    elif type.find('read') >= 0 or type.find('head') >= 0:
                        option_type = 'heading'
                    self.log(option_type, 'option_type')
                    # option_lang = option['option_languages']['2'] if option['option_languages']['2'] else option['option_languages']['1']
                    if self.is_wpml() and language_code:
                        option_data = self.get_convert_data_language(option_data, None, language_code,
                                                                     'option_languages')
                    meta_options_addons = dict()
                    meta_options_addons['name'] = option_data['option_name']
                    meta_options_addons['description'] = ''
                    meta_options_addons['position'] = 1
                    meta_options_addons['type'] = option_type
                    meta_options_addons['required'] = 1 if option_data['required'] == True else 0
                    meta_options_addons['title_format'] = 'heading'
                    meta_options_addons['display'] = 'select'
                    if type == 'multiswatch':
                        meta_options_addons['display'] = 'images'
                    if type.find('radio') >= 0:
                        meta_options_addons['display'] = 'radiobutton'
                    if option.get('sort_order'):
                        meta_options_addons['position'] = option['sort_order']
                    options_addons = list()
                    for value in option['values']:
                        option_value = value
                        if self.is_wpml() and language_code:
                            option_value = self.get_convert_data_language(option_value, None, language_code,
                                                                          'option_value_languages')
                        value_options_addons = dict()
                        value_options_addons['label'] = option_value['option_value_name']
                        value_options_addons['price'] = value['option_value_price'] if to_int(
                            value['option_value_price']) > 0 else ''
                        value_options_addons['price_type'] = 'quantity_based'
                        if option_value.get('option_value_image'):
                            option_image_process = self.process_image_before_import(option_value['option_value_image'],
                                                                                    '')
                            image_option_path = self.uploadImageConnector(option_image_process, self.add_prefix_path(
                                self.make_woocommerce_image_path(option_image_process['path']),
                                self._notice['target']['config']['image'].rstrip('/') + '/options'))
                            if not image_option_path:
                                continue
                            option_value_image = self.wp_image(image_option_path)
                            if not option_value_image:
                                continue
                            value_options_addons['image'] = option_value_image
                        options_addons.append(value_options_addons)
                    meta_options_addons['options'] = options_addons
                    meta_addons.append(meta_options_addons)

                # for meta_addon in meta_addons:
                product_meta_addons = {
                    '_product_addons': php_serialize(meta_addons),
                    '_product_addons_exclude_global': 0,
                    '_product_addons_old': php_serialize(meta_addons),
                    '_product_addons_converted': 'yes',
                }

                for meta_key, meta_value in product_meta_addons.items():
                    meta_insert = {
                        'post_id': product_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    all_queries.append(self.create_insert_query_connector("postmeta", meta_insert))
            else:
                if ((children_list and to_len(children_list) > self.VARIANT_LIMIT) or (
                        not children_list and self.count_child_from_option(
                    convert['options']) > self.VARIANT_LIMIT)) and (
                        (not self.is_wpml() and not self.is_polylang()) or not convert.get('language_code')):
                    self.log_variant_limit(product_id, convert, to_len(children_list))
                if children_list and to_len(children_list) <= self.VARIANT_LIMIT:
                    if to_len(children_list) >= self.WARNING_VARIANT_LIMIT:
                        self.warning_variant_limit(convert)
                    #### type 1 : attribute inside prd
                    attr_codes = dict()
                    # attributes_created = list()
                    if option_list and not self.is_woo2woo():
                        position = 0
                        for option in option_list:
                            pro_attr_code = self.get_pro_attr_code_default(option)
                            woo_attribute_id = self.get_woo_attribute_id(pro_attr_code, option['option_name'],
                                                                         language_code, option)
                            if not woo_attribute_id:
                                values = duplicate_field_value_from_list(option['values'], 'option_value_name')
                                pro_attr_new_code = pro_attr_code.replace('_', '-')
                                attribute_product = ' | '.join(values)
                                pro_attr[pro_attr_new_code] = {
                                    'name': option['option_name'],
                                    'value': attribute_product,
                                    'position': position,
                                    'is_visible': 1,
                                    'is_variation': 1,
                                    'is_taxonomy': 0
                                }
                                position += 1
                                attr_codes[pro_attr_code] = pro_attr_new_code
                                continue
                            # attributes_created.append(pro_attr_code)
                            attr_codes[pro_attr_code] = "pa_" + pro_attr_code
                            if option['values']:
                                for attr_value in option['values']:
                                    opt_value_id = self.get_woo_attribute_value(attr_value['option_value_name'],
                                                                                pro_attr_code, language_code,
                                                                                attr_value)
                                    if not opt_value_id:
                                        continue
                                    where_count_update = {
                                        'term_taxonomy_id': opt_value_id,
                                    }
                                    query_update = {
                                        'type': 'update',
                                        'query': "UPDATE _DBPRF_term_taxonomy SET `count` = `count` + 1 WHERE " + self.dict_to_where_condition(
                                            where_count_update)
                                    }
                                    self.import_data_connector(query_update, 'products')
                                    relationship = {
                                        'object_id': product_id,
                                        'term_taxonomy_id': opt_value_id,
                                        'term_order': 0
                                    }
                                    all_queries.append(
                                        self.create_insert_query_connector('term_relationships', relationship))

                            pro_attr["pa_" + pro_attr_code] = {
                                'name': "pa_" + urllib.parse.unquote_plus(pro_attr_code),
                                'value': '',
                                'position': position,
                                'is_visible': 1,
                                'is_variation': 1,
                                'is_taxonomy': 1
                            }
                            position += 1

                    for key_child, product_child in enumerate(children_list):
                        children_data = {
                            'post_author': 1,
                            'post_date': convert_format_time(product_child['created_at']) if product_child[
                                                                                                 'created_at'] and '0000-00-00' not in to_str(
                                product_child['created_at']) else get_current_time(),
                            'post_date_gmt': convert_format_time(product_child['created_at']) if product_child[
                                                                                                     'created_at'] and '0000-00-00' not in to_str(
                                product_child['created_at']) else get_current_time(),
                            'post_content': "",
                            'post_title': "Variation #" + to_str(product_id) + " of " + convert['name'],
                            'post_excerpt': '',
                            'post_status': "publish" if product_child['status'] else 'private',
                            'comment_status': 'open',
                            'ping_status': 'closed',
                            'post_password': '',
                            'post_name': 'product-' + to_str(product_id) + '-variation-' + to_str(key_child),
                            'to_ping': '',
                            'pinged': '',
                            'post_modified': product_child['updated_at'] if product_child[
                                'updated_at'] else get_current_time(),
                            'post_modified_gmt': product_child['updated_at'] if product_child[
                                'updated_at'] else get_current_time(),
                            'post_content_filtered': '',
                            'post_parent': product_id,
                            'guid': self._notice['target']['cart_url'].rstrip(
                                '/') + "/?product_variation=product-" + to_str(
                                product_id) + "-variation" + to_str(key_child),
                            'menu_order': 1 + key_child,
                            'post_type': "product_variation",
                            'post_mime_type': '',
                            'comment_count': 0
                        }
                        children_query = self.create_insert_query_connector('posts', children_data)
                        children_id = self.import_data_connector(children_query, 'product_child')

                        if not children_id:
                            msg = self.warning_import_entity('Product_variable', product_child['id'],
                                                             product_child['code'])
                            return response_warning(msg)

                        self.insert_map(self.TYPE_CHILD, product_child['id'], children_id, product_child['code'])
                        child_thumbnail_id = 0
                        config_image_path = self._notice['target']['config']['image_product'].rstrip('/') if not \
                        self._notice['target'][
                            'config'].get('site_id') else self._notice['target']['config']['image_product'].rstrip(
                            '/') + '/sites/' + to_str(self._notice['target']['config']['site_id'])
                        if self.is_wpml():
                            if product_child['thumb_image']['url'] or product_child['thumb_image']['path']:
                                image_process = self.process_image_before_import(product_child['thumb_image']['url'],
                                                                                 product_child['thumb_image']['path'])
                                rf_path = self.get_map_field_by_src(self.TYPE_PATH_IMAGE, None, image_process['url'], field='code_desc')
                                if not rf_path:
                                    image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                                    self.make_woocommerce_image_path(image_process['path']), config_image_path))

                                    if image_import_path:
                                        product_image = self.remove_prefix_path(image_import_path,
                                                                                self._notice['target']['config']['image_product'])
                                        _, image_details = self.get_sizes(image_process['url'])
                                        trid = self.get_new_trid()
                                        for lang_code, lang_name in self._notice['target']['languages'].items():
                                            rf_child_thumbnail_id = self.wp_image(product_image, image_details,
                                                                         check_exist=False, lang=lang_code)
                                            if rf_child_thumbnail_id:
                                                res = self.import_data_connector(self.rf_get_query_img_wpml(rf_child_thumbnail_id, lang_code, trid))
                                            if lang_code == language_code:
                                                child_thumbnail_id = rf_child_thumbnail_id
                        else:
                            if product_child['thumb_image']['url'] or product_child['thumb_image']['path']:
                                image_process = self.process_image_before_import(product_child['thumb_image']['url'],
                                                                                 product_child['thumb_image']['path'])
                                image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(
                                    self.make_woocommerce_image_path(image_process['path']), config_image_path))
                                if image_import_path:
                                    product_image = self.remove_prefix_path(image_import_path,
                                                                            self._notice['target']['config'][
                                                                                'image_product'])
                                    _, image_details = self.get_sizes(image_process['url'])
                                    child_thumbnail_id = self.wp_image(product_image, image_details)

                        if product_child.get('is_in_stock'):
                            child_stock_status = 'instock' if product_child['is_in_stock'] and to_int(
                                product_child['qty']) > 0 else 'outofstock'
                        else:
                            child_stock_status = 'outofstock' if product_child['manage_stock'] and to_int(
                                product_child['qty']) <= 0 else 'instock'
                        if self.is_woo2woo():
                            child_stock_status = product_child.get('is_in_stock', 'instock')
                        children_meta = {
                            '_stock_status': child_stock_status,
                            '_sku': product_child['sku'] if product_child['sku'] else '',
                            '_thumbnail_id': child_thumbnail_id,
                            '_virtual': "no",
                            '_downloadable': "no",
                            '_weight': product_child['weight'] if product_child['weight'] else '',
                            '_length': product_child['length'] if product_child['length'] else '',
                            '_width': product_child['width'] if product_child['width'] else '',
                            '_height': product_child['height'] if product_child['height'] else '',
                            '_manage_stock': "yes" if product_child['manage_stock'] else "no",
                            '_stock': product_child['qty'] if product_child['qty'] else 0,
                            '_regular_price': product_child['price'],
                            '_sale_price': product_child['special_price']['price'] if product_child['special_price'][
                                                                                          'price'] and (
                                                                                              self.to_timestamp(
                                                                                                  product_child[
                                                                                                      'special_price'][
                                                                                                      'end_date']) > time.time() or (
                                                                                                      product_child[
                                                                                                          'special_price'][
                                                                                                          'end_date'] == '0000-00-00' or
                                                                                                      product_child[
                                                                                                          'special_price'][
                                                                                                          'end_date'] == '0000-00-00 00:00:00' or
                                                                                                      product_child[
                                                                                                          'special_price'][
                                                                                                          'end_date'] == '' or
                                                                                                      product_child[
                                                                                                          'special_price'][
                                                                                                          'end_date'] == None or
                                                                                                      convert[
                                                                                                          'special_price'][
                                                                                                          'end_date'] == None)) else '',
                            '_price': product_child['special_price']['price'] if product_child['special_price'][
                                                                                     'price'] and (self.to_timestamp(
                                product_child['special_price']['end_date']) > time.time() or (product_child[
                                                                                                  'special_price'][
                                                                                                  'end_date'] == '0000-00-00' or
                                                                                              product_child[
                                                                                                  'special_price'][
                                                                                                  'end_date'] == '0000-00-00 00:00:00' or
                                                                                              product_child[
                                                                                                  'special_price'][
                                                                                                  'end_date'] == '' or
                                                                                              product_child[
                                                                                                  'special_price'][
                                                                                                  'end_date'] == None or
                                                                                              convert['special_price'][
                                                                                                  'end_date'] == None)) else
                            product_child['price'],
                            '_download_limit': "",
                            '_download_expiry': "",
                            '_downloadable_files': "",
                            '_variation_description': product_child.get('description', '') if product_child.get(
                                'description', '') != convert['description'] else ''
                        }
                        if convert['tax']['id'] or convert['tax']['code']:
                            tax_class = self.get_map_field_by_src(self.TYPE_TAX, convert['tax']['id'],
                                                                  convert['tax']['code'], field='code_desc')
                            children_meta['_tax_class'] = tax_class
                        if not children_meta['_price'] or to_decimal(children_meta['_price']) == 0:
                            children_meta['_price'] = children_meta['_regular_price']
                        if product_child['special_price']['price'] and (
                                self.to_timestamp(product_child['special_price']['end_date']) > time.time() or (
                                product_child['special_price']['end_date'] == '0000-00-00' or
                                product_child['special_price']['end_date'] == '0000-00-00 00:00:00' or
                                convert['special_price']['end_date'] == None)) or product_child['special_price'][
                            'end_date'] == '':
                            if product_child['special_price']['start_date']:
                                children_meta['_sale_price_dates_from'] = self.to_timestamp(
                                    product_child['special_price']['start_date'])
                            if product_child['special_price']['end_date']:
                                children_meta['_sale_price_dates_to'] = self.to_timestamp(
                                    product_child['special_price']['end_date'])
                        # mutil currency for children
                        if self._notice['target']['support'].get('wpml_currency'):
                            children_meta['_wcml_custom_prices_status'] = 1
                            for language_child, data_language_child in product_child['languages'].items():
                                if 'price' not in data_language_child:
                                    continue
                                language_child_target = self._notice['map']['languages'].get(language_child)
                                if not language_child_target:
                                    language_child_target = self._notice['map']['languages'].get(to_int(language_child))
                                if not language_child_target or to_str(language_child_target) == to_str(language_code):
                                    continue
                                lang_child_currency_switch = self._notice['target']['currency_map'].get(
                                    to_str(language_child_target))
                                if not lang_child_currency_switch:
                                    continue
                                children_meta['_regular_price_' + to_str(lang_child_currency_switch)] = \
                                    data_language_child['price']
                                children_meta['_wcml_schedule_' + to_str(lang_child_currency_switch)] = 0
                                children_meta['_sale_price_dates_from_' + to_str(lang_child_currency_switch)] = None
                                children_meta['_price_' + to_str(lang_child_currency_switch)] = data_language_child[
                                    'price']

                        for children_attribute in product_child['attributes']:
                            pro_attr_code = self.get_pro_attr_code_default(children_attribute)
                            # pro_attr_code = pro_attr_code.replace(' ', '_')
                            # if children_attribute['option_code']:
                            # 	pro_attr_code = children_attribute['option_code'].lower()
                            # 	pro_attr_code = pro_attr_code.replace(' ', '_')
                            # if pro_attr_code in attributes_created:
                            if pro_attr and pro_attr_code in pro_attr:
                                pro_attr_code = pro_attr_code
                            else:
                                pro_attr_code = 'pa_' + pro_attr_code
                            meta_value = self.get_slug_attr(children_attribute, language_code)
                            meta_value_default = self.get_slug_attr(children_attribute)
                            if self.is_wpml() and language_code and meta_value != meta_value_default:
                                meta_value = meta_value_default + '-' + language_code
                            # else:
                            # 	if isinstance(children_attribute['option_value_name'], bool):
                            # 		if children_attribute['option_value_name']:
                            # 			children_attribute['option_value_name'] = 'yes'
                            # 		else:
                            # 			children_attribute['option_value_name'] = 'no'
                            # 	meta_value = children_attribute['option_value_name'].strip()
                            # pro_attr_code = self.sanitize_title(pro_attr_code)
                            # pro_attr_code = pro_attr_code[:29].strip('-')
                            check_code = to_str(pro_attr_code).replace('pa_', '').replace('pa-', '')[:29].strip('-')
                            # if check_code in attr_codes:
                            # 	meta_key = "attribute_" + attr_codes[check_code]
                            # else:
                            meta_key = "attribute_" + to_str(pro_attr_code).strip('-')
                            # meta_key = meta_key.replace('pa-', 'pa_')
                            meta_key = meta_key[:42] if '%' not in pro_attr_code else meta_key
                            children_meta[meta_key] = meta_value
                        for meta_key, meta_value in children_meta.items():
                            meta_insert = {
                                'post_id': children_id,
                                'meta_key': meta_key,
                                'meta_value': meta_value
                            }
                            meta_query = self.create_insert_query_connector('postmeta', meta_insert)
                            all_queries.append(meta_query)

                        children_meta_lookup = {
                            'product_id': children_id,
                            'sku': children_meta['_sku'],
                            'virtual': 0,
                            'downloadable': 0,
                            'min_price': children_meta['_price'],
                            'max_price': children_meta['_price'],
                            'onsale': 0,
                            'stock_quantity': children_meta['_stock'] if children_meta['_stock'] else 0,
                            'stock_status': child_stock_status,
                            'rating_count': 0,
                            'average_rating': 0.00,
                            'total_sales': 0,
                        }
                        children_meta_lookup_query = self.create_insert_query_connector('wc_product_meta_lookup',
                                                                                        children_meta_lookup)
                        self.import_data_connector(children_meta_lookup_query, 'product_child')

                        if self.is_wpml():
                            key_check = self.get_key_check_default(product_child['attributes'])
                            product_variant_trid = None
                            if not convert.get('language_code'):
                                product_variant_trid = self.get_new_trid()
                                self.insert_map('trid', convert['id'], product_variant_trid, convert['code'], None,
                                                key_check)
                            else:

                                product_variant_trid_map = self.select_map(self._migration_id, 'trid', convert['id'],
                                                                           None, convert['code'], None, key_check)
                                if product_variant_trid_map:
                                    product_variant_trid = product_variant_trid_map['id_desc']
                            if product_variant_trid:
                                source_language_code = self._notice['target']['language_default']
                                default_language_code = language_code
                                if source_language_code == default_language_code:
                                    default_language_code = source_language_code
                                    source_language_code = None
                                wpml_child_data = {
                                    'element_type': 'post_product_variation',
                                    'element_id': children_id,
                                    'trid': product_variant_trid,
                                    'language_code': default_language_code,
                                    'source_language_code': source_language_code
                                }
                                wpml_child_query = self.create_insert_query_connector("icl_translations",
                                                                                      wpml_child_data)
                                wpml_child = self.import_data_connector(wpml_child_query, 'product_child')

        if pro_attr:
            update_attr_data = {
                'meta_value': php_serialize(pro_attr)
            }
            where_attr_update = {
                'post_id': product_id,
                'meta_key': '_product_attributes'
            }
            attribute_update_query = self.create_update_query_connector("postmeta", update_attr_data, where_attr_update)
            self.import_data_connector(attribute_update_query, 'product')
        if self.is_wpml():
            source_language_code = self._notice['target']['language_default']
            default_language_code = language_code
            if source_language_code == default_language_code:
                default_language_code = source_language_code
                source_language_code = None
            trid = convert.get('trid')
            if not trid:
                trid = self.get_new_trid()
            default_lang_map = get_value_by_key_in_dict(self._notice['map']['languages'],
                                                        get_value_by_key_in_dict(convert, 'language_default',
                                                                                 self._notice['src'][
                                                                                     'language_default']),
                                                        self._notice['target']['language_default'])
            wpml_default_data = {
                'element_type': 'post_product',
                'element_id': product_id,
                'trid': trid,
                'language_code': default_language_code,
                'source_language_code': source_language_code
            }
            wpml_default_query = self.create_insert_query_connector("icl_translations", wpml_default_data)
            wpml_default = self.import_data_connector(wpml_default_query, 'product')
            # prd lang
            if not convert.get('language_code'):
                list_target_id = list()
                for src_language_id, target_language_id in self._notice['map']['languages'].items():
                    if target_language_id in list_target_id or to_str(target_language_id) == to_str(
                            self._notice['target']['language_default']):
                        continue
                    list_target_id.append(target_language_id)
                    product_lang = self.get_convert_data_language(convert, src_language_id)
                    product_lang['trid'] = trid
                    product_lang['language_code'] = target_language_id
                    product_import = self.product_import(product_lang, product, products_ext)
                    if product_import['result'] == 'success':
                        self.after_product_import(product_import['data'], product_lang, product, products_ext)
        if self.is_polylang():
            source_language_code = self._notice['target']['language_default']
            language_code = convert.get('language_code')
            if not language_code:
                language_code = source_language_code
                source_language_code = None
            post_trans_id = self.get_map_field_by_src('product_lang', convert['id'])
            if not post_trans_id:
                term_data = {
                    'name': 'pll_' + to_str(product_id),
                    'slug': 'pll_' + to_str(product_id),
                    'term_group': 0,
                }
                term_query = self.create_insert_query_connector('terms', term_data)
                term_lang_id = self.import_data_connector(term_query, 'category')
                if not term_lang_id:
                    return response_warning('product ' + to_str(convert['id']) + ' not lang.')
                def_data = {
                    language_code: product_id
                }
                trans_taxonomy_data = {
                    'term_id': term_lang_id,
                    'taxonomy': 'post_translations',
                    'description': php_serialize(def_data),
                    'parent': 0,
                    'count': 0,
                }
                taxonomy_trans_query = self.create_insert_query_connector('term_taxonomy', trans_taxonomy_data)
                post_trans_id = self.import_data_connector(taxonomy_trans_query, 'category')
                self.insert_map('product_lang', convert['id'], post_trans_id)

            if post_trans_id:
                all_two_queries = list()
                query_lang = {
                    'type': 'select',
                    'query': "SELECT * FROM `_DBPRF_term_taxonomy` WHERE `taxonomy` = 'post_translations' AND term_taxonomy_id = " + to_str(
                        post_trans_id)
                }
                product_lang_data = self.get_connector_data(self.get_connector_url('query'),
                                                            {'query': json.dumps(query_lang)})
                if product_lang_data and product_lang_data['data']:
                    lang_value = php_unserialize(product_lang_data['data'][0]['description'])
                    if not lang_value:
                        lang_value = dict()
                    if not language_code in lang_value:
                        lang_value[language_code] = product_id
                    data_set = {
                        'description': php_serialize(lang_value)
                    }
                    where = {
                        'taxonomy': 'post_translations',
                        'term_taxonomy_id': post_trans_id
                    }
                    update_query = self.create_update_query_connector('term_taxonomy', data_set, where)
                    all_two_queries.append(update_query)

                relation_lang_data = {
                    'object_id': product_id,
                    'term_taxonomy_id': self._notice['target']['support']['polylang_product'].get(language_code, 0),
                    'term_order': 0,
                }
                relation_lang_query = self.create_insert_query_connector('term_relationships', relation_lang_data)
                all_two_queries.append(relation_lang_query)

                relation_trans_data = {
                    'object_id': product_id,
                    'term_taxonomy_id': post_trans_id,
                    'term_order': 0,
                }
                relation_trans_query = self.create_insert_query_connector('term_relationships', relation_trans_data)
                all_two_queries.append(relation_trans_query)
                if all_two_queries:
                    self.import_multiple_data_connector(all_two_queries, 'product')
            if not convert.get('language_code'):
                list_target_id = list()
                for src_language_id, target_language_id in self._notice['map']['languages'].items():
                    if target_language_id in list_target_id or to_str(target_language_id) == to_str(
                            self._notice['target']['language_default']) or not convert['languages'].get(
                        src_language_id):
                        continue
                    list_target_id.append(target_language_id)
                    product_lang = self.get_convert_data_language(convert, src_language_id)
                    product_lang['language_code'] = target_language_id
                    product_import = self.product_import(product_lang, product, products_ext)
                    if product_import['result'] == 'success':
                        self.after_product_import(product_import['data'], product_lang, product, products_ext)
        if all_queries:
            self.import_multiple_data_connector(all_queries, 'product')
        return response_success()

    def addition_product_import(self, convert, product, products_ext):
        return response_success()

    def finish_product_import(self):
        if self.is_variant_limit:
            self._notice['config']['variant_limit'] = True
        return response_success()

    # TODO: CUSTOMER
    # def prepare_customers_import(self):
    #     return self

    # def prepare_customers_export(self):
    # 	return self

    def prepare_customers_import(self):
        if self._notice['config'].get('cus_pass'):
            delete_query = {
                'type': 'query',
                'query': "DELETE FROM `_DBPRF_options` WHERE option_name = 'LEPP_TYPE' OR option_name = 'LEPP_URL'"
            }
            config_delete = self.import_data_connector(delete_query)
            all_queries = list()
            type_data = {
                'option_name': 'LEPP_TYPE',
                'option_value': self._notice['src']['cart_type'],
                'autoload': 'yes'
            }
            type_query = self.create_insert_query_connector('options', type_data)
            all_queries.append(type_query)
            url_data = {
                'option_name': 'LEPP_URL',
                'option_value': "https://fabricfactory.mylittleshindig.com",
                'autoload': 'yes'
            }
            url_query = self.create_insert_query_connector('options', url_data)
            all_queries.append(url_query)

            if all_queries:
                self.import_multiple_data_connector(all_queries, 'customer')
        return self

    def get_customers_main_export(self):
        id_src = self._notice['process']['customers']['id_src']
        limit = self._notice['setting']['customers']
        prefix = self._notice['src']['config']['table_prefix']
        if self._notice['src']['config'].get('site_id'):
            prefix = to_str(prefix).replace(to_str(self._notice['src']['config'].get('site_id')) + '_', '')
        query = {
            'type': 'select',
            'query': "SELECT * FROM " + prefix + "users u LEFT JOIN " + prefix + "usermeta um ON u.ID = um.user_id WHERE (um.meta_key = '_DBPRF_capabilities' AND um.meta_value LIKE '%customer%' OR um.meta_value LIKE '%subscriber%') AND ID > " + to_str(
                id_src) + " ORDER BY ID ASC LIMIT " + to_str(limit)
        }
        # customers = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        customers = self.select_data_connector(query, 'customers')
        if not customers or customers['result'] != 'success':
            return response_error()
        return customers

    def get_customers_ext_export(self, customers):
        url_query = self.get_connector_url('query')
        customers_ids = duplicate_field_value_from_list(customers['data'], 'ID')
        customer_ext_queries = {
            'user_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_usermeta WHERE user_id IN " + self.list_to_in_condition(
                    customers_ids),
            }
        }

        if self._notice['src']['support'].get('customer_point_rewards'):
            customer_ext_queries['wc_points_rewards_user_points'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_wc_points_rewards_user_points WHERE (order_id IS NULL OR order_id = '') AND user_id IN " + self.list_to_in_condition(
                    customers_ids),
            }
            customer_ext_queries['wc_points_rewards_user_points_log'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_wc_points_rewards_user_points_log WHERE (order_id IS NULL OR order_id = '') AND user_id IN " + self.list_to_in_condition(
                    customers_ids),
            }

        # customers_ext = self.get_connector_data(url_query,
        #                                         {'serialize': True, 'query': json.dumps(customer_ext_queries)})
        customers_ext = self.select_multiple_data_connector(customer_ext_queries, 'customers')
        if not customers_ext or customers_ext['result'] != 'success':
            return response_error()

        return customers_ext

    def convert_customer_export(self, customer, customers_ext):
        customer_data = self.construct_customer()
        customer_data = self.add_construct_default(customer_data)
        customer_data['id'] = customer['ID']
        customer_data['code'] = customer['user_login']
        customer_data['username'] = customer['user_nicename']
        customer_data['email'] = customer['user_email']
        customer_data['password'] = customer['user_pass']
        customer_data['website'] = customer['user_url']
        customer_data['user_url'] = customer['user_url']
        customer_data['active'] = True
        customer_data['created_at'] = convert_format_time(customer['user_registered'])
        customer_meta = get_list_from_list_by_field(customers_ext['data']['user_meta'], 'user_id', customer['ID'])

        customer_data['first_name'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'first_name', 'meta_value'))
        customer_data['last_name'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'last_name', 'meta_value'))

        prefix = self._notice['src']['config']['table_prefix']
        capabilities = to_str(prefix) + '_capabilities'
        customer_data['capabilities'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', capabilities, 'meta_value'))
        # billing
        address_data = self.construct_customer_address()
        address_data['code'] = to_str(customer['ID']) + "_1"
        address_data['first_name'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_first_name', 'meta_value'))
        address_data['last_name'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_last_name', 'meta_value'))
        address_data['address_1'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_address_1', 'meta_value'))
        address_data['address_2'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_address_2', 'meta_value'))
        address_data['city'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_city', 'meta_value'))
        address_data['postcode'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_postcode', 'meta_value'))
        address_data['telephone'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_phone', 'meta_value'))
        address_data['company'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_company', 'meta_value'))
        address_data['fax'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_fax', 'meta_value'))
        address_data['country']['country_code'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_country', 'meta_value'))
        address_data['country']['code'] = address_data['country']['country_code']
        address_data['country']['name'] = self.get_country_name_by_code(address_data['country']['country_code'])
        address_data['state']['state_code'] = to_str(
            get_row_value_from_list_by_field(customer_meta, 'meta_key', 'billing_state', 'meta_value'))
        address_data['state']['code'] = address_data['state']['state_code']
        address_data['default']['billing'] = True
        if address_data['address_1'] or address_data['address_2']:
            customer_data['address'].append(address_data)
        # shipping
        shipping_address = self.get_list_from_list_by_field_as_first_key(customer_meta, 'meta_key', 'shipping_')
        if shipping_address:
            shipping_data = self.construct_customer_address()
            shipping_data['code'] = to_str(customer['ID']) + "_2"
            shipping_data['first_name'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_first_name', 'meta_value'))
            shipping_data['last_name'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_last_name', 'meta_value'))
            shipping_data['address_1'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_address_1', 'meta_value'))
            shipping_data['address_2'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_address_2', 'meta_value'))
            shipping_data['city'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_city', 'meta_value'))
            shipping_data['postcode'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_postcode', 'meta_value'))
            shipping_data['telephone'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_phone', 'meta_value'))
            shipping_data['company'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_company', 'meta_value'))
            shipping_data['fax'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_fax', 'meta_value'))
            shipping_data['country']['country_code'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_country', 'meta_value'))
            shipping_data['country']['code'] = shipping_data['country']['country_code']
            shipping_data['country']['name'] = self.get_country_name_by_code(shipping_data['country']['code'])
            shipping_data['state']['state_code'] = to_str(
                get_row_value_from_list_by_field(shipping_address, 'meta_key', 'shipping_state', 'meta_value'))
            shipping_data['state']['code'] = shipping_data['state']['state_code']
            shipping_data['default']['shipping'] = True
            if shipping_data['address_1'] or shipping_data['address_2']:
                customer_data['address'].append(shipping_data)
        # customer_data['first_name'] = customer_data['first_name'] if customer_data['first_name']: address_data['first_name']
        # customer_data['last_name'] = customer_data['last_name'] if customer_data['last_name']: address_data['last_name']

        # TODO: Plugin WooCommerce Points and Rewards
        if self._notice['src']['support'].get('customer_point_rewards'):
            customer_point_rewards = dict()
            customer_point_rewards['reward_point'] = list()
            customer_point_rewards['reward_point_log'] = list()
            customer_point_rewards['points_balance'] = get_row_value_from_list_by_field(customer_meta, 'meta_key',
                                                                                        'wc_points_balance',
                                                                                        'meta_value')
            wc_points_rewards_user_points = get_list_from_list_by_field(
                customers_ext['data']['wc_points_rewards_user_points'], 'user_id', customer['ID'])
            if wc_points_rewards_user_points:
                for points_rewards_user_points in wc_points_rewards_user_points:
                    reward_point = dict()
                    reward_point['points'] = points_rewards_user_points['points']
                    reward_point['points_balance'] = points_rewards_user_points['points_balance']
                    reward_point['order_id'] = points_rewards_user_points['order_id']
                    reward_point['created_at'] = points_rewards_user_points['date']
                    customer_point_rewards['reward_point'].append(reward_point)
            wc_points_rewards_user_points_log = get_list_from_list_by_field(
                customers_ext['data']['wc_points_rewards_user_points_log'], 'user_id', customer['ID'])
            if wc_points_rewards_user_points_log:
                for points_rewards_user_points_log in wc_points_rewards_user_points_log:
                    reward_point_log = dict()
                    reward_point_log['points'] = points_rewards_user_points_log['points']
                    reward_point_log['type'] = points_rewards_user_points_log['type']
                    reward_point_log['user_points_id'] = points_rewards_user_points_log['user_points_id']
                    reward_point_log['order_id'] = points_rewards_user_points_log['order_id']
                    reward_point_log['admin_user_id'] = points_rewards_user_points_log['admin_user_id']
                    reward_point_log['data'] = points_rewards_user_points_log['data']
                    reward_point_log['created_at'] = points_rewards_user_points_log['date']
                    customer_point_rewards['reward_point_log'].append(reward_point_log)
            customer_data['point_rewards'] = customer_point_rewards
        return response_success(customer_data)

    def get_customer_id_import(self, convert, customer, customers_ext):
        return customer['ID']

    def check_customer_import(self, convert, customer, customers_ext):
        return True if self.get_map_field_by_src(self.TYPE_CUSTOMER, convert['id'], convert['code']) else False

    def router_customer_import(self, convert, customer, customers_ext):
        return response_success('customer_import')

    def before_customer_import(self, convert, customer, customers_ext):
        return response_success()

    def customer_import(self, convert, customer, customers_ext):
        prefix = self._notice['target']['config']['table_prefix']
        if self._notice['target']['config'].get('site_id'):
            prefix = to_str(prefix).replace(to_str(self._notice['target']['config'].get('site_id')) + '_', '')
        customer_data = {
            'user_login': get_value_by_key_in_dict(convert, 'username', convert['email']),
            'user_pass': to_str(convert.get('password')),
            'user_nicename': to_str(get_value_by_key_in_dict(convert, 'username', convert['email']))[:50],
            'user_email': convert['email'] if convert['email'] else '',
            # 'user_url': customer.get('user_url'),
            'user_registered': convert_format_time(convert['created_at']) if convert[
                'created_at'] else get_current_time(),
            'user_status': 1 if convert.get('active') else 0,
            'display_name': get_value_by_key_in_dict(convert, 'display_name',
                                                     to_str(convert['first_name']) + ' ' + to_str(convert['last_name']))
        }

        if convert.get('user_url'):
            customer_data['user_url'] = convert['user_url']

        if (self._notice['config']['pre_cus']):
            # delete_customer = self.delete_target_customer(convert['id'])
            customer_data['ID'] = convert['id']
        customer_query = self.create_insert_query_connector(prefix + "users", customer_data, prefix=False)
        customer_id = self.import_customer_data_connector(customer_query, True, convert['id'])
        if not customer_id:
            msg = self.warning_import_entity('Customer', convert['id'], convert['code'])
            return response_error()

        self.insert_map(self.TYPE_CUSTOMER, convert['id'], customer_id, convert['code'])
        return response_success(customer_id)

    def after_customer_import(self, customer_id, convert, customer, customers_ext):
        prefix = self._notice['target']['config']['table_prefix']
        if self._notice['target']['config'].get('site_id'):
            prefix = to_str(prefix)[::-1].replace('_' + to_str(self._notice['target']['config'].get('site_id')), '', 1)[
                     ::-1]
        user_meta = dict()
        all_queries_first = list()
        role = ''
        if convert['group_id'] and self._notice['support']['customer_group_map']:
            role = self.get_map_customer_group(convert['group_id'])
        if not role:
            role = 'customer'
        capabilities = php_serialize({role: True})
        if self.is_woo2woo() and convert.get('capabilities'):
            capabilities = convert['capabilities']

        reward_point = 0
        if convert.get('rewards'):
            for reward in convert['rewards']:
                reward_point = reward['points']
        user_meta_import_first = {
            'nickname': get_value_by_key_in_dict(convert, 'username', convert['email']),
            'first_name': convert['first_name'],
            'last_name': convert['last_name'],
            'rich_editing': "true",
            'comment_shortcuts': "false",
            'admin_color': "fresh",
            'use_ssl': False,
            'show_admin_bar_front': "true",
            # '_DBPRF_capabilities': php_serialize({'customer': True}),
            '_DBPRF_capabilities': capabilities,
            '_DBPRF_user_level': 0,
            'wc_points_balance': convert['point_rewards']['points_balance'] if convert.get('point_rewards') and convert[
                'point_rewards'].get('points_balance') else 0,
            '_my_reward_points': reward_point
        }
        for meta_key, meta_value in user_meta_import_first.items():
            meta_insert = {
                'user_id': customer_id,
                'meta_key': meta_key,
                'meta_value': meta_value
            }
            meta_query = self.create_insert_query_connector(prefix + "usermeta", meta_insert, prefix=False)
            all_queries_first.append(meta_query)
        if all_queries_first:
            self.import_multiple_data_connector(all_queries_first, 'customer')

        all_queries = list()
        if convert['address']:
            bill_data = False
            ship_data = False
            for address in convert['address']:
                if address['default']['billing']:
                    bill_data = address
                if address['default']['shipping']:
                    ship_data = address
            if not bill_data:
                bill_data = convert['address'][0]
            if not ship_data:
                ship_data = convert['address'][1] if 1 in convert['address'] else bill_data
            user_meta = {
                'billing_country': bill_data['country']['country_code'],
                'billing_first_name': bill_data['first_name'],
                'billing_last_name': bill_data['last_name'],
                'billing_company': bill_data['company'],
                'billing_address_1': bill_data['address_1'],
                'billing_address_2': bill_data['address_2'],
                'billing_city': bill_data['city'],
                'billing_state': bill_data['state']['state_code'] if bill_data['state']['state_code'] else
                bill_data['state']['name'],
                'billing_postcode': bill_data['postcode'],
                'billing_email': convert['email'],
                'billing_phone': get_value_by_key_in_dict(bill_data, 'telephone',
                                                          get_value_by_key_in_dict(convert, 'telephone', '')),
                'billing_fax': bill_data['fax'],
                'shipping_country': ship_data['country']['country_code'],
                'shipping_first_name': ship_data['first_name'],
                'shipping_last_name': ship_data['last_name'],
                'shipping_company': ship_data['company'],
                'shipping_address_1': ship_data['address_1'],
                'shipping_address_2': ship_data['address_2'],
                'shipping_city': ship_data['city'],
                'shipping_state': ship_data['state']['state_code'] if ship_data['state']['state_code'] else
                ship_data['state']['name'],
                'shipping_postcode': ship_data['postcode'],
                'shipping_email': convert['email'],
                'shipping_phone': ship_data['telephone'],
                'shipping_fax': ship_data['fax'],
            }
            for meta_key, meta_value in user_meta.items():
                meta_insert = {
                    'user_id': customer_id,
                    'meta_key': meta_key,
                    'meta_value': meta_value
                }
                meta_query = self.create_insert_query_connector("usermeta", meta_insert)
                all_queries.append(meta_query)
            if all_queries:
                self.import_multiple_data_connector(all_queries, 'customer')

        if self._notice['target']['support'].get('plugin_woo_admin') or self.convert_version(
                self._notice['target']['config']['version'], 2) > 399:
            wc_customer_lookup_data = {
                'user_id': customer_id,
                'username': get_value_by_key_in_dict(convert, 'username', convert['email']),
                'first_name': convert.get('first_name', ''),
                'last_name': convert.get('last_name', ''),
                'email': convert.get('email'),
                'date_last_active': convert.get('updated_at'),
                'date_registered': convert.get('created_at'),
                'country': convert['address'][0]['country']['country_code'] if to_len(convert['address']) > 0 else '',
                'postcode': convert['address'][0].get('postcode', '') if to_len(convert['address']) > 0 else '',
                'city': convert['address'][0].get('city', '') if to_len(convert['address']) > 0 else '',
                'state': convert['address'][0]['state']['state_code'] if to_len(convert['address']) > 0 and
                                                                         convert['address'][0]['state'][
                                                                             'state_code'] else '',
            }
            self.import_data_connector(
                self.create_insert_query_connector('wc_customer_lookup', wc_customer_lookup_data), 'customer')

        # TODO: Plugin WooCommerce Points and Rewards
        if self._notice['target']['support'].get('customer_point_rewards'):
            if convert.get('point_rewards'):
                all_query_second = list()
                if convert['point_rewards'].get('reward_point'):
                    for reward_point in convert['point_rewards']['reward_point']:
                        wc_points_rewards_user_points = {
                            'user_id': customer_id,
                            'points': reward_point.get('points', 0),
                            'points_balance': reward_point.get('points_balance', 0),
                            'order_id': None,
                            'date': reward_point.get('created_at', get_current_time())
                        }
                        all_query_second.append(self.create_insert_query_connector("wc_points_rewards_user_points",
                                                                                   wc_points_rewards_user_points))
                if convert['point_rewards'].get('reward_point_log'):
                    for reward_point_log in convert['point_rewards']['reward_point_log']:
                        user_points_id = None
                        if reward_point_log.get('user_points_id'):
                            user_points_id = self.get_map_field_by_src(self.TYPE_CUSTOMER,
                                                                       reward_point_log['user_points_id'])
                            if not user_points_id:
                                user_points_id = None
                        wc_points_rewards_user_points_log = {
                            'user_id': customer_id,
                            'points': reward_point_log.get('points', 0),
                            'type': reward_point_log.get('type', 0),
                            'user_points_id': user_points_id,
                            'admin_user_id': 1,
                            'data': reward_point_log.get('data', 0),
                            'order_id': None,
                            'date': reward_point_log.get('created_at', get_current_time())
                        }
                        all_query_second.append(self.create_insert_query_connector("wc_points_rewards_user_points_log",
                                                                                   wc_points_rewards_user_points_log))
                if all_query_second:
                    self.import_multiple_data_connector(all_query_second, 'customer')

        return response_success()

    def addition_customer_import(self, convert, customer, customers_ext):
        return response_success()

    # TODO: ORDER
    def prepare_orders_import(self):
        return self

    def prepare_orders_export(self):
        return self

    def get_orders_main_export(self):
        id_src = self._notice['process']['orders']['id_src']
        limit = self._notice['setting']['orders']
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft') AND ID > " + to_str(
                id_src) + " ORDER BY ID ASC LIMIT " + to_str(limit)
        }
        # orders = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        orders = self.select_data_connector(query, 'orders')
        if not orders or orders['result'] != 'success':
            return response_error()
        return orders

    def get_orders_by_created_at(self, created_at):
        id_src = self._notice['process']['orders']['id_src']
        limit = self._notice['setting']['orders']
        query = {
            'type': 'select',
            'query': f"SELECT * FROM _DBPRF_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft') AND post_date >= '{created_at}' AND ID > {id_src} ORDER BY ID ASC LIMIT {limit}"
        }
        # orders = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        orders = self.select_data_connector(query, 'orders')
        if not orders or orders['result'] != 'success':
            return response_error()
        return orders

    def get_orders_ext_export(self, orders):
        url_query = self.get_connector_url('query')
        order_ids = duplicate_field_value_from_list(orders['data'], 'ID')
        customer_ext_queries = {
            'woocommerce_order_items': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_order_items WHERE order_id IN  " + self.list_to_in_condition(
                    order_ids),
            },
            'order_note': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_comments WHERE comment_post_ID IN " + self.list_to_in_condition(
                    order_ids),
            },
            'order_refund': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_posts WHERE post_type = 'shop_order_refund' AND post_parent IN " + self.list_to_in_condition(
                    order_ids),
            },
            'order_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN " + self.list_to_in_condition(order_ids),
            },
        }

        orders_ext = self.select_multiple_data_connector(customer_ext_queries, 'orders')
        if not orders_ext or orders_ext['result'] != 'success':
            return response_error()
        # product_option_value_ids = duplicate_field_value_from_list(orders_ext['data']['order_option'], 'product_option_value_id')
        # order_recurrings = duplicate_field_value_from_list(orders_ext['data']['order_recurring'], 'order_recurring_id')
        order_item_ids = duplicate_field_value_from_list(orders_ext['data']['woocommerce_order_items'], 'order_item_id')

        comment_ids = duplicate_field_value_from_list(orders_ext['data']['order_note'], 'comment_ID')

        refund_ids = duplicate_field_value_from_list(orders_ext['data']['order_refund'], 'ID')
        post_meta_ids = list(set(refund_ids + order_ids))
        cus_list = get_list_from_list_by_field(orders_ext['data']['order_meta'], 'meta_key', '_customer_user')
        cus_ids = list()
        if cus_list:
            cus_ids = duplicate_field_value_from_list(cus_list, 'meta_value')

        orders_ext_rel_queries = {
            'woocommerce_order_itemmeta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_woocommerce_order_itemmeta WHERE order_item_id IN " + self.list_to_in_condition(
                    order_item_ids),
            },
            'order_note_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_commentmeta WHERE comment_id IN " + self.list_to_in_condition(
                    comment_ids),
            },
            'postmeta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN " + self.list_to_in_condition(post_meta_ids),
            },
            'user': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_users WHERE ID IN " + self.list_to_in_condition(cus_ids),
            },
            'user_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_usermeta WHERE meta_key IN ('first_name','last_name') AND user_id IN  " + self.list_to_in_condition(
                    cus_ids),
            }
        }

        if self._notice['src']['support'].get('customer_point_rewards'):
            orders_ext_rel_queries['wc_points_rewards_user_points'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_wc_points_rewards_user_points WHERE order_id IN " + self.list_to_in_condition(
                    order_ids),
            }
            orders_ext_rel_queries['wc_points_rewards_user_points_log'] = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_wc_points_rewards_user_points_log WHERE order_id IN " + self.list_to_in_condition(
                    order_ids),
            }

        orders_ext_rel = self.select_multiple_data_connector(orders_ext_rel_queries, 'orders')
        if not orders_ext_rel or orders_ext_rel['result'] != 'success':
            return response_error()
        orders_ext = self.sync_connector_object(orders_ext, orders_ext_rel)

        pro_list = get_list_from_list_by_field(orders_ext_rel['data']['woocommerce_order_itemmeta'], 'meta_key',
                                               '_product_id')
        pro_ids = duplicate_field_value_from_list(pro_list, 'meta_value')

        orders_ext_third_rel_queries = {
            'products_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN " + self.list_to_in_condition(pro_ids),
            },
        }
        orders_ext_third_rel = self.get_connector_data(url_query, {'serialize': True,
                                                                   'query': json.dumps(orders_ext_third_rel_queries)})
        if not orders_ext_third_rel or orders_ext_third_rel['result'] != 'success':
            return response_error()
        orders_ext = self.sync_connector_object(orders_ext, orders_ext_third_rel)
        return orders_ext

    def convert_order_export(self, order, orders_ext):
        order_data = self.construct_order()
        order_data = self.add_construct_default(order_data)
        order_data['id'] = order['ID']
        order_data['status'] = order['post_status']
        # order data
        order_items = get_list_from_list_by_field(orders_ext['data']['woocommerce_order_items'], 'order_id',
                                                  order['ID'])
        shipping = get_row_from_list_by_field(order_items, 'order_item_type', 'shipping')
        taxes = get_list_from_list_by_field(order_items, 'order_item_type', 'tax')
        tax_names = list()
        total_tax = 0.0
        if taxes:
            tax_names = duplicate_field_value_from_list(taxes, 'order_item_name')

            for tax in taxes:
                order_tax_metas = get_list_from_list_by_field(orders_ext['data']['woocommerce_order_itemmeta'],
                                                              'order_item_id', tax['order_item_id'])
                total_tax += to_decimal(self.get_value_metadata(order_tax_metas, 'tax_amount', 0.0))
                total_tax += to_decimal(self.get_value_metadata(order_tax_metas, 'shipping_tax_amount', 0.0))
        if 'postmeta' in orders_ext['data']:
            order_meta = get_list_from_list_by_field(orders_ext['data']['postmeta'], 'post_id', order['ID'])
        else:
            order_meta = get_list_from_list_by_field(orders_ext['data']['order_meta'], 'post_id', order['ID'])
        ord_number = get_row_value_from_list_by_field(order_meta, 'meta_key', '_order_number', 'meta_value')
        if ord_number and self._notice['src']['support'].get('plugin_pre_ord'):
            order_data['order_number'] = ord_number
        order_data['tax']['title'] = '|'.join(tax_names) if tax_names else 'Tax'
        order_data['tax']['amount'] = total_tax if total_tax else self.get_value_metadata(order_meta, '_order_tax',
                                                                                          0.0000)
        order_data['shipping']['title'] = shipping['order_item_name'] if shipping else 'Shipping'
        order_data['shipping']['amount'] = self.get_value_metadata(order_meta, '_order_shipping',
                                                                   0.0000)  # _order_shipping_tax
        discount_title = get_row_value_from_list_by_field(order_items, 'order_item_type', 'coupon', 'order_item_name')
        order_data['discount']['title'] = discount_title if discount_title else 'Discount'
        order_data['discount']['amount'] = self.get_value_metadata(order_meta, '_cart_discount', 0.0000)
        order_data['total']['title'] = 'Total'
        order_data['total']['amount'] = self.get_value_metadata(order_meta, '_order_total', 0.0000)
        order_data['subtotal']['title'] = 'Total'
        order_data['subtotal']['amount'] = to_decimal(
            self.get_value_metadata(order_meta, '_order_total', 0.0000)) - to_decimal(
            self.get_value_metadata(order_meta, '_cart_discount', 0.0000)) - to_decimal(
            order_data['tax']['amount']) - to_decimal(order_data['shipping']['amount'])
        order_data['currency'] = self.get_value_metadata(order_meta, '_order_currency', 'meta_value')
        order_data['created_at'] = convert_format_time(order['post_date'])
        order_data['updated_at'] = convert_format_time(order['post_modified'])
        # order customer
        order_customer = self.construct_order_customer()
        order_customer = self.add_construct_default(order_customer)
        order_customer_src = self.get_value_metadata(order_meta, '_customer_user', '')
        if order_customer_src and to_int(order_customer_src) > 0:
            customer_src = get_row_from_list_by_field(orders_ext['data']['user'], 'ID', order_customer_src)
            customer_meta_src = get_list_from_list_by_field(orders_ext['data']['user_meta'], 'user_id',
                                                            order_customer_src)
            if customer_src:
                order_customer['id'] = order_customer_src
                order_customer['code'] = get_value_by_key_in_dict(customer_src, 'user_login', '')
                order_customer['email'] = get_value_by_key_in_dict(customer_src, 'user_email',
                                                                   self.get_value_metadata(order_meta, '_billing_email',
                                                                                           ''))
                order_customer['username'] = get_value_by_key_in_dict(customer_src, 'display_name', '')
            order_customer['first_name'] = self.get_value_metadata(customer_meta_src, 'first_name',
                                                                   self.get_value_metadata(order_meta,
                                                                                           '_billing_first_name', ''))
            order_customer['last_name'] = self.get_value_metadata(customer_meta_src, 'last_name',
                                                                  self.get_value_metadata(order_meta,
                                                                                          '_billing_last_name', ''))
        else:
            order_customer['email'] = self.get_value_metadata(order_meta, '_billing_email', '')
            order_customer['username'] = order_customer['email']
            order_customer['first_name'] = self.get_value_metadata(order_meta, '_billing_first_name', '')
            order_customer['last_name'] = self.get_value_metadata(order_meta, '_billing_last_name', '')
        order_data['customer'] = order_customer

        # TODO: Plugin WooCommerce Points and Rewards
        if self._notice['src']['support'].get('customer_point_rewards'):
            customer_point_rewards = dict()
            customer_point_rewards['reward_point'] = list()
            customer_point_rewards['reward_point_log'] = list()
            wc_points_rewards_user_points = get_list_from_list_by_field(
                orders_ext['data']['wc_points_rewards_user_points'], 'order_id', order['ID'])
            if wc_points_rewards_user_points:
                for points_rewards_user_points in wc_points_rewards_user_points:
                    reward_point = dict()
                    reward_point['points'] = points_rewards_user_points['points']
                    reward_point['points_balance'] = points_rewards_user_points['points_balance']
                    reward_point['user_id'] = points_rewards_user_points['user_id']
                    reward_point['created_at'] = points_rewards_user_points['date']
                    customer_point_rewards['reward_point'].append(reward_point)
            wc_points_rewards_user_points_log = get_list_from_list_by_field(
                orders_ext['data']['wc_points_rewards_user_points_log'], 'order_id', order['ID'])
            if wc_points_rewards_user_points_log:
                for points_rewards_user_points_log in wc_points_rewards_user_points_log:
                    reward_point_log = dict()
                    reward_point_log['points'] = points_rewards_user_points_log['points']
                    reward_point_log['type'] = points_rewards_user_points_log['type']
                    reward_point_log['user_points_id'] = points_rewards_user_points_log['user_points_id']
                    reward_point_log['user_id'] = points_rewards_user_points_log['user_id']
                    reward_point_log['admin_user_id'] = points_rewards_user_points_log['admin_user_id']
                    reward_point_log['data'] = points_rewards_user_points_log['data']
                    reward_point_log['created_at'] = points_rewards_user_points_log['date']
                    customer_point_rewards['reward_point_log'].append(reward_point_log)
            order_data['point_rewards'] = customer_point_rewards

        # customer address
        customer_address = self.construct_order_address()
        customer_address = self.add_construct_default(customer_address)
        customer_address['first_name'] = self.get_value_metadata(order_meta, '_billing_first_name', '')
        customer_address['last_name'] = self.get_value_metadata(order_meta, '_billing_last_name', '')
        customer_address['email'] = self.get_value_metadata(order_meta, '_billing_email', '')
        customer_address['address_1'] = self.get_value_metadata(order_meta, '_billing_address_1', '')
        customer_address['address_2'] = self.get_value_metadata(order_meta, '_billing_address_2', '')
        customer_address['city'] = self.get_value_metadata(order_meta, '_billing_city', '')
        customer_address['postcode'] = self.get_value_metadata(order_meta, '_billing_postcode', '')
        customer_address['telephone'] = self.get_value_metadata(order_meta, '_billing_phone', '')
        customer_address['company'] = self.get_value_metadata(order_meta, '_billing_company', '')
        customer_address['country']['code'] = self.get_value_metadata(order_meta, '_billing_country', '')
        customer_address['country']['country_code'] = self.get_value_metadata(order_meta, '_billing_country', '')
        customer_address['country']['name'] = self.get_country_name_by_code(customer_address['country']['country_code'])
        customer_address['state']['state_code'] = self.get_value_metadata(order_meta, '_billing_state', '')
        customer_address['state']['code'] = customer_address['state']['state_code']
        order_data['customer_address'] = customer_address
        # billing address
        order_billing = self.construct_order_address()
        order_billing = self.add_construct_default(order_billing)
        order_billing['first_name'] = self.get_value_metadata(order_meta, '_billing_first_name', '')
        order_billing['last_name'] = self.get_value_metadata(order_meta, '_billing_last_name', '')
        order_billing['email'] = self.get_value_metadata(order_meta, '_billing_email', '')
        order_billing['address_1'] = self.get_value_metadata(order_meta, '_billing_address_1', '')
        order_billing['address_2'] = self.get_value_metadata(order_meta, '_billing_address_2', '')
        order_billing['city'] = self.get_value_metadata(order_meta, '_billing_city', '')
        order_billing['postcode'] = self.get_value_metadata(order_meta, '_billing_postcode', '')
        order_billing['telephone'] = self.get_value_metadata(order_meta, '_billing_phone', '')
        order_billing['company'] = self.get_value_metadata(order_meta, '_billing_company', '')
        order_billing['country']['code'] = self.get_value_metadata(order_meta, '_billing_country', '')
        order_billing['country']['country_code'] = self.get_value_metadata(order_meta, '_billing_country', '')
        order_billing['country']['name'] = self.get_country_name_by_code(order_billing['country']['country_code'])
        order_billing['state']['state_code'] = self.get_value_metadata(order_meta, '_billing_state', '')
        order_billing['state']['code'] = order_billing['state']['state_code']
        order_billing['code'] = self.convert_attribute_code(
            to_str(order_billing['first_name']) + '-' + to_str(order_billing['last_name']) + '-' + to_str(
                order_billing['address_1']) + '-' + to_str(order_billing['address_2']))
        order_data['billing_address'] = order_billing
        # shipping address
        order_delivery = self.construct_order_address()
        order_delivery = self.add_construct_default(order_delivery)
        order_delivery['first_name'] = self.get_value_metadata(order_meta, '_shipping_first_name', '')
        order_delivery['last_name'] = self.get_value_metadata(order_meta, '_shipping_last_name', '')
        order_delivery['email'] = self.get_value_metadata(order_meta, '_shipping_email', '')
        order_delivery['address_1'] = self.get_value_metadata(order_meta, '_shipping_address_1', '')
        order_delivery['address_2'] = self.get_value_metadata(order_meta, '_shipping_address_2', '')
        order_delivery['city'] = self.get_value_metadata(order_meta, '_shipping_city', '')
        order_delivery['postcode'] = self.get_value_metadata(order_meta, '_shipping_postcode', '')
        order_delivery['telephone'] = self.get_value_metadata(order_meta, '_shipping_phone',
                                                              '') if self.get_value_metadata(order_meta,
                                                                                             '_shipping_phone',
                                                                                             '') else self.get_value_metadata(
            order_meta, '_shipping_Phone_No', '')
        order_delivery['company'] = self.get_value_metadata(order_meta, '_shipping_company', '')
        order_delivery['country']['code'] = self.get_value_metadata(order_meta, '_shipping_country', '')
        order_delivery['country']['country_code'] = self.get_value_metadata(order_meta, '_shipping_country', '')
        order_delivery['country']['name'] = self.get_country_name_by_code(order_delivery['country']['country_code'])
        order_delivery['state']['state_code'] = self.get_value_metadata(order_meta, '_shipping_state', '')
        order_delivery['state']['code'] = order_delivery['state']['state_code']
        order_delivery['code'] = self.convert_attribute_code(
            to_str(order_delivery['first_name']) + '-' + to_str(order_delivery['last_name']) + '-' + to_str(
                order_delivery['address_1']) + '-' + to_str(order_delivery['address_2']))
        order_data['shipping_address'] = order_delivery

        # order_data['user_history'] = self.get_value_metadata(order_meta, '_user_history', '')

        order_products = get_list_from_list_by_field(order_items, 'order_item_type', 'line_item')
        order_items = list()
        for order_product in order_products:
            order_product_metas = get_list_from_list_by_field(orders_ext['data']['woocommerce_order_itemmeta'],
                                                              'order_item_id', order_product['order_item_id'])
            qty = self.get_value_metadata(order_product_metas, '_qty', 1)
            if to_int(qty) == 0:
                qty = 1
            order_item_subtotal = self.get_value_metadata(order_product_metas, '_line_subtotal', 0.0000)

            order_item = self.construct_order_item()
            order_item = self.add_construct_default(order_item)
            order_item['id'] = order_product['order_item_id']
            
            ###### Tony fix code

            order_item['product']['variation_id']=self.get_value_metadata(order_product_metas,'_variation_id',None)
            order_item['product']['id'] = self.get_value_metadata(order_product_metas, '_product_id',None)
            # if to_int(self.get_value_metadata(order_product_metas, '_variation_id',
            #                                   self.get_value_metadata(order_product_metas, '_product_id', 0))) == 0:
            #     order_item['product']['id'] = self.get_value_metadata(order_product_metas, '_product_id', 0)
            # else:
            #     order_item['product']['id'] = self.get_value_metadata(order_product_metas, '_variation_id',
            #                                                           self.get_value_metadata(order_product_metas,
            #                                                                                   '_product_id', 0))
            order_item['product']['code'] = self.get_value_metadata(order_product_metas, '_product_code', None)
            product_meta = get_list_from_list_by_field(orders_ext['data']['products_meta'], 'post_id',
                                                       order_item['product']['id'])
            order_item['product']['sku'] = self.get_value_metadata(product_meta, '_sku', '')
            order_item['product']['name'] = order_product['order_item_name']
            order_item['qty'] = to_decimal(qty) if qty != '' else 1
            order_item['price'] = to_decimal(order_item_subtotal) / to_decimal(qty) if (qty != 0 and qty != '') else 0
            order_item['original_price'] = to_decimal(order_item_subtotal) / to_decimal(qty) if (
                    qty != 0 and qty != '') else 0
            order_item['tax_amount'] = self.get_value_metadata(order_product_metas, '_line_tax', 0.0000)
            order_item['subtotal'] = order_item_subtotal
            order_item['total'] = self.get_value_metadata(order_product_metas, '_line_total', 0.0000)
            order_item['options'] = list()
            if order_product['order_item_type'] == 'line_item':
                order_item_options = list()
                keys = {'_qty', '_tax_class', '_product_id', '_variation_id', '_line_subtotal', '_line_subtotal_tax',
                        '_line_total', '_line_tax', '_line_tax_data', '_original_order_item_id'}
                for order_product_meta in order_product_metas:
                    if order_product_meta['meta_key'] not in keys and not order_product_meta.get('meta_key',
                                                                                                 '').startswith('_'):
                        order_item_option = self.construct_order_item_option()
                        # order_item_option['option_name'] = order_product_meta['meta_key']
                        order_item_option['option_name'] = unquote(order_product_meta['meta_key'])
                        if order_item_option['option_name'] and 'pa_' in order_item_option['option_name']:
                            continue
                        order_item_option['option_value_name'] = order_product_meta['meta_value']
                        # unquote(order_product['order_item_name'])
                        order_item_options.append(order_item_option)
                order_item['options'] = order_item_options

            order_items.append(order_item)

        order_data['items'] = order_items

        order_notes = get_list_from_list_by_field(orders_ext['data']['order_note'], 'comment_post_ID', order['ID'])
        order_history = list()
        for order_note in order_notes:
            order_note_meta = get_list_from_list_by_field(orders_ext['data']['order_note_meta'], 'comment_id',
                                                          order_note['comment_ID'])
            order_history = self.construct_order_history()
            order_history = self.add_construct_default(order_history)
            order_history['id'] = order_note['comment_ID']
            order_history['status'] = order_note['comment_approved']
            order_history['comment'] = order_note['comment_content']
            order_history['notified'] = self.get_value_metadata(order_note_meta, 'is_customer_note', False)
            order_history['created_at'] = convert_format_time(order_note['comment_date'])

            order_data['history'].append(order_history)

        order_payment = self.construct_order_payment()
        order_payment = self.add_construct_default(order_payment)
        order_payment['id'] = order['ID']
        order_payment['method'] = self.get_value_metadata(order_meta, '_payment_method')
        order_payment['title'] = self.get_value_metadata(order_meta, '_payment_method_title')

        # custom order_number plugin WooCommerce Sequential Order Numbers
        # order_data['order_number'] = self.get_value_metadata(order_meta, '_order_number', '')
        # order_data['order_number_formatted'] = self.get_value_metadata(order_meta, '_order_number_formatted', '')
        # order_data['order_number_meta'] = self.get_value_metadata(order_meta, '_order_number_meta', '')

        order_data['payment'] = order_payment
        return response_success(order_data)

    def get_order_id_import(self, convert, order, orders_ext):
        return order['ID']

    def check_order_import(self, convert, order, orders_ext):
        return self.get_map_field_by_src(self.TYPE_ORDER, convert['id'], convert['code'])

    def update_order_after_demo(self, order_id, convert, order, orders_ext):
        all_queries = list()
        delete_query = list()
        # order item
        delete_query_child = {
            'type': 'delete',
            'query': 'DELETE FROM _DBPRF_woocommerce_order_itemmeta WHERE order_item_id IN (SELECT order_item_id FROM _DBPFF_woocommerce_order_items WHERE order_id = ' + to_str(
                order_id) + ')'
        }
        delete_query.append(delete_query_child)
        delete_query.append(self.create_delete_query_connector('woocommerce_order_items', {'order_id': order_id}))
        self.import_multiple_data_connector(delete_query, 'delete_ord_update')
        order_items = convert['items']
        for item in order_items:
            order_item_data = {
                'order_item_name': item['product']['name'],
                'order_item_type': 'line_item',
                'order_id': order_id
            }
            order_item_query = self.create_insert_query_connector("woocommerce_order_items", order_item_data)
            order_item_id = self.import_data_connector(order_item_query, 'order')
            product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, item['product']['id'])
            if not product_id:
                product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, None, item['product']['id'])
            if not product_id:
                product_id = 0

            order_item_meta = {
                '_qty': item['qty'],
                '_tax_class': '',
                '_product_id': product_id,
                '_variation_id': '',
                '_line_subtotal': item['subtotal'],
                '_line_total': item['total'],
                '_line_subtotal_tax': 0,
                '_line_tax': 0,
                '_line_tax_data': php_serialize({
                    'total': 0,
                    'subtotal': 0
                }),
            }
            for meta_key, meta_value in order_item_meta.items():
                meta_insert = {
                    'order_item_id': order_item_id,
                    'meta_key': meta_key,
                    'meta_value': meta_value
                }
                meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                all_queries.append(meta_query)
            for option in item['options']:
                meta_insert = {
                    'order_item_id': order_item_id,
                    'meta_key': option['option_name'],
                    'meta_value': option['option_value_name']
                }
                meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                all_queries.append(meta_query)
        return response_success()

    def router_order_import(self, convert, order, orders_ext):
        return response_success('order_import')

    def before_order_import(self, convert, order, orders_ext):
        return response_success()

    def order_import(self, convert, order, orders_ext):
        customer = convert['customer']
        customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, customer['id'], customer['code'])
        if not customer_id:
            customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, None, customer['code'])
            if not customer_id:
                customer_id = 0

        order_status = self._notice['map']['order_status'][convert['status']] if convert['status'] in \
                                                                                 self._notice['map'][
                                                                                     'order_status'] else 'wc-completed'
        order_key = self.uniqid('order_')
        order_data = {
            'post_author': customer_id,
            'post_date': convert['created_at'] if convert['created_at'] else get_current_time(),
            'post_date_gmt': convert['created_at'] if convert['created_at'] else get_current_time(),
            'post_content': '',
            'post_title': 'Order',
            'post_excerpt': '',
            'post_status': order_status,
            'comment_status': 'open',
            'ping_status': 'closed',
            'post_password': order_key,
            'post_name': 'order',
            'to_ping': '',
            'pinged': '',
            'post_modified': convert['updated_at'] if convert['updated_at'] else get_current_time(),
            'post_modified_gmt': convert['updated_at'] if convert['updated_at'] else get_current_time(),
            'post_content_filtered': '',
            'post_parent': 0,
            'guid': '',
            'menu_order': 0,
            'post_type': 'shop_order',
            'post_mime_type': '',
            'comment_count': 0,
        }

        order_query = self.create_insert_query_connector("posts", order_data)

        order_id = self.import_order_data_connector(order_query, True, convert['id'])
        if not order_id:
            msg = self.warning_import_entity('Order', convert['id'], convert['code'])
            return response_error(msg)
        self.insert_map(self.TYPE_ORDER, convert['id'], order_id, convert['code'])
        return response_success(order_id)

    def after_order_import(self, order_id, convert, order, orders_ext):
        all_queries = list()
        # guid
        guid = self._notice['target']['cart_url'] + "?post_type=shop_order&p=" + to_str(order_id)
        guid_data = {
            'guid': guid
        }
        where_guid = {
            'ID': order_id,
            'post_type': 'shop_order'
        }
        guid_order_update_query = self.create_update_query_connector("posts", guid_data, where_guid)
        all_queries.append(guid_order_update_query)
        # order meta
        order_key = self.uniqid('order_')
        customer = convert['customer']
        billing_address = convert['billing_address']
        shipping_address = convert['shipping_address']
        customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, customer['id'], customer['code'])
        if not customer_id:
            customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, None, customer['code'])
            if not customer_id:
                customer_id = 0

        payment = convert['payment']
        payment_method = ''
        if get_value_by_key_in_dict(payment, 'title', ''):
            if 'paypal' in get_value_by_key_in_dict(payment, 'title', '').lower():
                payment_method = 'paypal'
            if 'delivery' in get_value_by_key_in_dict(payment, 'title', '').lower():
                payment_method = 'cod'
        currency = self._notice['target']['currency_default']
        if convert.get("currency"):
            currency = convert['currency']
        if not currency:
            currency = "USD"
        try:
            countries_alpha_3 = json_decode(self.COUNTRIES_3)
        except:
            countries_alpha_3 = {}
        billing_country_code = get_value_by_key_in_dict(billing_address['country'], 'country_code',
                                                        '') if billing_address and billing_address['country'] else ''
        billing_country = countries_alpha_3.get(billing_country_code) if len(
            billing_country_code) > 2 else billing_country_code
        shipping_country_code = get_value_by_key_in_dict(shipping_address['country'], 'country_code',
                                                         '') if shipping_address and shipping_address['country'] else ''
        shipping_country = countries_alpha_3.get(shipping_country_code) if len(
            shipping_country_code) > 2 else shipping_country_code

        order_meta = {
            '_order_key': "wc_" + order_key,
            '_order_currency': currency,
            '_prices_include_tax': 'no',
            '_customer_user': customer_id,
            '_order_shipping': get_value_by_key_in_dict(convert['shipping'], 'amount', ''),
            '_billing_country': billing_country,
            '_billing_first_name': get_value_by_key_in_dict(billing_address, 'first_name', ''),
            '_billing_last_name': get_value_by_key_in_dict(billing_address, 'last_name', ''),
            '_billing_company': get_value_by_key_in_dict(billing_address, 'company', ''),
            '_billing_address_1': get_value_by_key_in_dict(billing_address, 'address_1', ''),
            '_billing_address_2': get_value_by_key_in_dict(billing_address, 'address_2', ''),
            '_billing_city': get_value_by_key_in_dict(billing_address, 'city', ''),
            '_billing_state': get_value_by_key_in_dict(billing_address['state'], 'state_code',
                                                       billing_address['state']['name']) if billing_address and
                                                                                            billing_address[
                                                                                                'state'] else '',
            '_billing_postcode': get_value_by_key_in_dict(billing_address, 'postcode', ''),
            '_billing_email': get_value_by_key_in_dict(billing_address, 'email',
                                                       get_value_by_key_in_dict(convert['customer'], 'email', '')),
            '_billing_phone': get_value_by_key_in_dict(billing_address, 'telephone', ''),
            '_shipping_country': shipping_country,
            '_shipping_first_name': get_value_by_key_in_dict(shipping_address, 'first_name', ''),
            '_shipping_last_name': get_value_by_key_in_dict(shipping_address, 'last_name', ''),
            '_shipping_company': get_value_by_key_in_dict(shipping_address, 'company', ''),
            '_shipping_address_1': get_value_by_key_in_dict(shipping_address, 'address_1', ''),
            '_shipping_address_2': get_value_by_key_in_dict(shipping_address, 'address_2', ''),
            '_shipping_city': get_value_by_key_in_dict(shipping_address, 'city', ''),
            '_shipping_state': get_value_by_key_in_dict(shipping_address['state'], 'state_code',
                                                        shipping_address['state']['name']) if shipping_address and
                                                                                              shipping_address[
                                                                                                  'state'] else '',
            '_shipping_postcode': get_value_by_key_in_dict(shipping_address, 'postcode', ''),
            '_shipping_email': get_value_by_key_in_dict(shipping_address, 'email',
                                                        get_value_by_key_in_dict(convert['customer'], 'email', '')),
            '_shipping_phone': get_value_by_key_in_dict(shipping_address, 'telephone', ''),
            '_payment_method': get_value_by_key_in_dict(payment, 'method', payment_method),
            '_payment_method_title': get_value_by_key_in_dict(payment, 'title', ''),
            '_cart_discount': '-' + to_str(convert['discount']['amount']),
            '_cart_discount_tax': 0,
            '_order_tax': convert['tax']['amount'],
            '_order_shipping_tax': convert['shipping']['amount'],
            '_order_total': convert['total']['amount'],
            '_download_permissions_granted': 'yes'
        }
        if billing_address:
            order_meta['_billing_address_index'] = ''
            for key in ['_billing_first_name', '_billing_last_name', '_billing_country', '_billing_company',
                        '_billing_address_1', '_billing_address_2', '_billing_city', '_billing_state',
                        '_billing_postcode', '_billing_phone', '_billing_email']:
                if order_meta.get(key):
                    order_meta['_billing_address_index'] += to_str(order_meta[key]) + ' '

        if shipping_address:
            order_meta['_shipping_address_index'] = ''
            for key in ['_shipping_first_name', '_shipping_last_name', '_shipping_country', '_shipping_company',
                        '_shipping_address_1', '_shipping_address_2', '_shipping_city', '_shipping_state',
                        '_shipping_postcode', '_shipping_phone', '_shipping_email']:
                if order_meta.get(key):
                    order_meta['_shipping_address_index'] += order_meta[key] + ' '

        if self._notice['config']['pre_ord']:
            order_number = convert['id']
            if convert.get('order_number'):
                order_number = convert['order_number']
            order_number = to_str(order_number).replace('#', '')
            order_meta['_order_number'] = order_number
            order_meta['_alg_wc_custom_order_number'] = order_number
            order_meta['_sequential_order_number_id'] = order_number
            order_meta['_sequential_order_number'] = order_number
            order_meta['_start_sequential_order_number'] = order_number
            order_meta['_order_number_formatted'] = order_number

        # custom order_number plugin WooCommerce Sequential Order Numbers
        # order_meta['_order_number'] = get_value_by_key_in_dict(convert, 'order_number', '')
        # order_meta['_order_number_formatted'] = get_value_by_key_in_dict(convert, 'order_number_formatted', '')
        # order_meta['_order_number_meta'] = get_value_by_key_in_dict(convert, 'order_number_meta', '')

        for meta_key, meta_value in order_meta.items():
            meta_insert = {
                'post_id': order_id,
                'meta_key': meta_key,
                'meta_value': meta_value
            }
            meta_query = self.create_insert_query_connector("postmeta", meta_insert)
            all_queries.append(meta_query)

        # order item
        order_items = convert['items']
        for item in order_items:
            order_item_data = {
                'order_item_name': item['product']['name'],
                'order_item_type': 'line_item',
                'order_id': order_id
            }
            order_item_query = self.create_insert_query_connector("woocommerce_order_items", order_item_data)
            order_item_id = self.import_data_connector(order_item_query, 'order')
            product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, item['product']['id'], item['product']['code'])
            if self.is_wpml():
                product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, item['product']['id'],
                                                       item['product']['code'],
                                                       self._notice['target']['language_default'])
            # if not product_id:
            # 	product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, None, item['product']['id'])
            if not product_id:
                product_id = 0
            else:
                product_download_data = self.get_product_download_data(product_id)

                if product_download_data:
                    for key, download_data in product_download_data.items():
                        download_count = 0
                        file = download_data['file']
                        for item_download in item.get('downloads', []):
                            name = self._notice['target'][
                                       'cart_url'] + "/wp-content/uploads/downloadable/" + item_download.get('file')
                            if file == name:
                                self.log(item_download, 'item_download')
                                download_count = item_download['download_count']
                                break
                        download_data_per = self.get_download_data(product_id)
                        access_expires = None
                        downloads_remaining = None
                        if download_data_per:
                            access_expires = download_data_per.get('_download_expiry')
                            downloads_remaining = download_data_per.get('_download_limit')
                        woocommerce_downloadable_product_permissions = {
                            'download_id': download_data['id'],
                            'product_id': product_id,
                            'order_id': order_id,
                            'order_key': "wc_" + order_key,
                            'user_email': get_value_by_key_in_dict(convert['customer'], 'email', ''),
                            'user_id': customer_id,
                            'access_granted': convert['updated_at'] if convert['updated_at'] else get_current_time(),
                            'download_count': download_count,
                            # 'access_expires': access_expires,
                            'downloads_remaining': downloads_remaining,
                        }
                        # self.log(woocommerce_downloadable_product_permissions,'data_per')
                        order_query = self.create_insert_query_connector("woocommerce_downloadable_product_permissions",
                                                                         woocommerce_downloadable_product_permissions)
                        self.import_order_data_connector(order_query, True, convert['id'])
            subtotal = item.get('subtotal', to_decimal(item['price']) * to_int(item['qty']))
            if to_int(subtotal) == 0:
                subtotal = to_decimal(item['price']) * to_int(item['qty'])
            order_item_meta = {
                '_qty': item['qty'],
                '_tax_class': '',
                '_product_id': product_id,
                '_variation_id': '',
                '_line_subtotal': subtotal,
                '_line_total': to_decimal(subtotal) + to_decimal(item['discount_amount']),
                '_line_subtotal_tax': 0,
                '_line_tax': 0,
                '_line_tax_data': php_serialize({
                    'total': 0,
                    'subtotal': 0
                }),
            }
            if product_id == 0 and item['product']['sku']:
                order_item_meta['SKU'] = item['product']['sku']
            for meta_key, meta_value in order_item_meta.items():
                meta_insert = {
                    'order_item_id': order_item_id,
                    'meta_key': meta_key,
                    'meta_value': meta_value
                }
                meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                all_queries.append(meta_query)
            for option in item['options']:
                meta_insert = {
                    'order_item_id': order_item_id,
                    'meta_key': option['option_name'],
                    'meta_value': option['option_value_name']
                }
                meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                all_queries.append(meta_query)
        # discount
        discount = convert['discount']
        if discount['amount'] != '' and to_decimal(discount['amount']) != 0:
            order_discount_data = {
                'order_item_name': 'Discount',
                'order_item_type': "fee",
                'order_id': order_id
            }
            order_discount_query = self.create_insert_query_connector("woocommerce_order_items", order_discount_data)
            order_discount_import = self.import_data_connector(order_discount_query, 'order')

            if order_discount_import:
                order_item_meta = {
                    '_tax_class': '-' + to_str(abs(to_decimal(discount['amount']))),
                    '_line_total': '-' + to_str(abs(to_decimal(discount['amount']))),
                    '_line_tax': 0,
                    '_line_subtotal': '-' + to_str(to_decimal(discount['amount'])),
                    '_line_tax_data': 'a:2:{s:5:"total"a:0:{}s:8:"subtotal"a:0:{}}',
                    '_line_subtotal_tax': 0
                }
                for meta_key, meta_value in order_item_meta.items():
                    meta_discount_insert = {
                        'order_item_id': order_discount_import,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_discount_insert)
                    all_queries.append(meta_query)
        # tax
        tax = convert['tax']
        if tax['amount'] != '' and to_decimal(tax['amount']) != 0:
            order_item_data = {
                'order_item_name': 'VAT',
                'order_item_type': "fee",
                'order_id': order_id
            }
            order_tax_query = self.create_insert_query_connector("woocommerce_order_items", order_item_data)

            order_tax_id = self.import_data_connector(order_tax_query, 'order')
            if order_tax_id:
                order_item_meta = {
                    '_line_total': tax['amount'],
                    '_line_tax': 0,
                    '_line_subtotal': tax['amount'],
                    '_line_tax_data': '',
                    '_line_subtotal_tax': 0
                }
                for meta_key, meta_value in order_item_meta.items():
                    meta_insert = {
                        'order_item_id': order_tax_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                    all_queries.append(meta_query)
        # shipping
        shipping = convert['shipping']
        if to_decimal(shipping['amount']) != 0 or shipping['title'] != '':
            order_shipping_data = {
                'order_item_name': shipping['title'] if shipping['title'] and shipping[
                    'title'].lower() != 'none' else 'Shipping',
                'order_item_type': "shipping",
                'order_id': order_id
            }
            order_shipping_query = self.create_insert_query_connector("woocommerce_order_items", order_shipping_data)

            order_shipping_id = self.import_data_connector(order_shipping_query, 'order')
            if order_shipping_id:
                order_item_meta = {
                    'method_id': "flat_rate",
                    'cost': to_decimal(shipping['amount']),
                    'taxes': php_serialize(list())
                }
                for meta_key, meta_value in order_item_meta.items():
                    meta_insert = {
                        'order_item_id': order_shipping_id,
                        'meta_key': meta_key,
                        'meta_value': meta_value
                    }
                    meta_query = self.create_insert_query_connector("woocommerce_order_itemmeta", meta_insert)
                    all_queries.append(meta_query)

        # TODO: order note
        notes = convert['history']
        for note in notes:
            if note.get('comment'):
                order_note_data = {
                    'comment_post_ID': order_id,
                    'comment_author': "admin" if 'customer_note' in note and not note[
                        'customer_note'] else 'WooCommerce',
                    'comment_author_email': "",
                    'comment_author_url': "",
                    'comment_author_IP': "",
                    'comment_date': note['created_at'] if note['created_at'] else convert['updated_at'],
                    'comment_date_gmt': note['created_at'] if note['created_at'] else convert['updated_at'],
                    'comment_content': get_value_by_key_in_dict(note, 'comment', ''),
                    'comment_karma': 0,
                    'comment_approved': 1 if to_int(note['status']) == 1 else 0,
                    'comment_agent': "WooCommerce",
                    'comment_type': "order_note",
                    'comment_parent': 0,
                    'user_id': 0
                }
                order_note_query = self.create_insert_query_connector("comments", order_note_data)

                order_note_id = self.import_data_connector(order_note_query, 'order')
                if order_note_id:
                    # if 'customer_note' in note and not note['customer_note']:
                    # 	continue
                    # else:
                    if convert.get('notified'):
                        meta_insert = {
                            'comment_id': order_note_id,
                            'meta_key': 'is_customer_note',
                            'meta_value': 1
                        }
                        meta_query = self.create_insert_query_connector("commentmeta", meta_insert)
                        all_queries.append(meta_query)

        # if convert.get('discount'):
        # 	discount_data = convert['discount']
        # 	order_note_discount_data= {
        # 		'comment_post_ID': order_id,
        # 		'comment_author': "admin",
        # 		'comment_author_email': "",
        # 		'comment_author_url': "",
        # 		'comment_author_IP': "",
        # 		'comment_date': get_current_time(),
        # 		'comment_date_gmt':get_current_time(),
        # 		'comment_content': get_value_by_key_in_dict(discount_data, 'title', ''),
        # 		'comment_karma': 0,
        # 		'comment_approved': 1,
        # 		'comment_agent': "WooCommerce",
        # 		'comment_type': "order_note",
        # 		'comment_parent': 0,
        # 		'user_id': 0
        # 	}
        # 	order_note_discount_data_query = self.create_insert_query_connector("comments", order_note_discount_data)
        # 	order_note_discount_data_id = self.import_data_connector(order_note_discount_data_query, 'order')
        # 	if order_note_discount_data_id:
        # 			meta_insert = {
        # 				'comment_id': order_note_discount_data_id,
        # 				'meta_key': 'is_customer_note',
        # 				'meta_value': 1
        # 			}
        # 			meta_query = self.create_insert_query_connector("commentmeta", meta_insert)
        # 			all_queries.append(meta_query)
        if convert.get('payment'):
            payment_method = convert['payment']
            if payment_method.get('title'):
                order_note_data_payment_method = {
                    'comment_post_ID': order_id,
                    'comment_author': "admin",
                    'comment_author_email': "",
                    'comment_author_url': "",
                    'comment_author_IP': "",
                    'comment_date': get_current_time(),
                    'comment_date_gmt': get_current_time(),
                    'comment_content': 'Payment Method: ' + to_str(
                        get_value_by_key_in_dict(payment_method, 'title', '')),
                    'comment_karma': 0,
                    'comment_approved': 1,
                    'comment_agent': "WooCommerce",
                    'comment_type': "order_note",
                    'comment_parent': 0,
                    'user_id': 0
                }
                order_note_data_payment_method_query = self.create_insert_query_connector("comments",
                                                                                          order_note_data_payment_method)
                self.import_data_connector(order_note_data_payment_method_query, 'order')

        if convert.get('shipping'):
            shipping_method = convert['shipping']
            if shipping_method.get('title'):
                order_note_data_shipping_method = {
                    'comment_post_ID': order_id,
                    'comment_author': "admin",
                    'comment_author_email': "",
                    'comment_author_url': "",
                    'comment_author_IP': "",
                    'comment_date': get_current_time(),
                    'comment_date_gmt': get_current_time(),
                    'comment_content': 'Shipping Method: ' + to_str(
                        get_value_by_key_in_dict(shipping_method, 'title', '')),
                    'comment_karma': 0,
                    'comment_approved': 1,
                    'comment_agent': "WooCommerce",
                    'comment_type': "order_note",
                    'comment_parent': 0,
                    'user_id': 0
                }
                order_note_data_shipping_method_query = self.create_insert_query_connector("comments",
                                                                                           order_note_data_shipping_method)
                self.import_data_connector(order_note_data_shipping_method_query, 'order')
        # this is private notes
        # if order_note_payment_method_id:
        # 	meta_insert = {
        # 		'comment_id': order_note_payment_method_id,
        # 		'meta_key': 'is_customer_note',
        # 		'meta_value': 1
        # 	}
        # 	meta_query = self.create_insert_query_connector("commentmeta", meta_insert)
        # 	all_queries.append(meta_query)

        if convert.get('shipping_payment'):
            shiping_payment = convert['shipping_payment']
            if shiping_payment.get('title'):
                order_note_data_shiping_payment = {
                    'comment_post_ID': order_id,
                    'comment_author': "admin",
                    'comment_author_email': "",
                    'comment_author_url': "",
                    'comment_author_IP': "",
                    'comment_date': get_current_time(),
                    'comment_date_gmt': get_current_time(),
                    'comment_content': 'Shipping Payment: ' + to_str(
                        get_value_by_key_in_dict(shiping_payment, 'title', '')),
                    'comment_karma': 0,
                    'comment_approved': 1,
                    'comment_agent': "WooCommerce",
                    'comment_type': "order_note",
                    'comment_parent': 0,
                    'user_id': 0
                }
                order_note_data_shiping_payment_query = self.create_insert_query_connector("comments",
                                                                                           order_note_data_shiping_payment)
                self.import_data_connector(order_note_data_shiping_payment_query, 'order')
        # this is private notes
        # if order_note_payment_id:
        # 	meta_insert = {
        # 		'comment_id': order_note_payment_id,
        # 		'meta_key': 'is_customer_note',
        # 		'meta_value': 1
        # 	}
        # 	meta_query = self.create_insert_query_connector("commentmeta", meta_insert)
        # 	all_queries.append(meta_query)
        # end: order notes

        # TODO: Plugin WooCommerce Points and Rewards
        if self._notice['target']['support'].get('customer_point_rewards'):
            if convert.get('point_rewards'):
                if convert['point_rewards'].get('reward_point'):
                    for reward_point in convert['point_rewards']['reward_point']:
                        user_id = 0
                        if reward_point.get('user_id'):
                            user_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, reward_point['user_id'])
                            if not user_id:
                                customer_id = 0
                        wc_points_rewards_user_points = {
                            'user_id': user_id,
                            'points': reward_point.get('points', 0),
                            'points_balance': reward_point.get('points_balance', 0),
                            'order_id': order_id,
                            'date': reward_point.get('created_at', get_current_time())
                        }
                        all_queries.append(self.create_insert_query_connector("wc_points_rewards_user_points",
                                                                              wc_points_rewards_user_points))
                if convert['point_rewards'].get('reward_point_log'):
                    for reward_point_log in convert['point_rewards']['reward_point_log']:
                        user_id = 0
                        if reward_point_log.get('user_points_id'):
                            user_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, reward_point_log['user_id'])
                            if not user_id:
                                user_id = 0
                        user_points_id = None
                        if reward_point_log.get('user_points_id'):
                            user_points_id = self.get_map_field_by_src(self.TYPE_CUSTOMER,
                                                                       reward_point_log['user_points_id'])
                            if not user_points_id:
                                user_points_id = None
                        wc_points_rewards_user_points_log = {
                            'user_id': user_id,
                            'points': reward_point_log.get('points', 0),
                            'type': reward_point_log.get('type', 0),
                            'user_points_id': user_points_id,
                            'admin_user_id': 1,
                            'data': reward_point_log.get('data', 0),
                            'order_id': order_id,
                            'date': reward_point_log.get('created_at', get_current_time())
                        }
                        all_queries.append(self.create_insert_query_connector("wc_points_rewards_user_points_log",
                                                                              wc_points_rewards_user_points_log))

        customer_lookup_id = 0
        if customer_id:
            customer_lookup_id = self._get_customer_lookup_id(customer_id)

        if self._notice['target']['support'].get('plugin_woo_admin') or self.convert_version(
                self._notice['target']['config']['version'], 2) > 399:
            wc_order_stats_data = {
                'order_id': order_id,
                'parent_id': 0,
                'date_created': convert['updated_at'] if convert['updated_at'] else get_current_time(),
                'date_created_gmt': convert['updated_at'] if convert['updated_at'] else get_current_time(),
                'num_items_sold': to_len(order_items) if order_items else 0,
                'total_sales': convert['total']['amount'],
                'tax_total': convert['tax']['amount'],
                'shipping_total': convert['shipping']['amount'],
                'net_total': convert['total']['amount'],
                'returning_customer': 1,
                'status': self._notice['map']['order_status'][convert['status']] if convert['status'] in
                                                                                    self._notice['map'][
                                                                                        'order_status'] else 'wc-completed',
                'customer_id': customer_lookup_id,
            }
            all_queries.append(self.create_insert_query_connector('wc_order_stats', wc_order_stats_data))

        if all_queries:
            self.import_multiple_data_connector(all_queries, 'order')
        return response_success()

    def addition_order_import(self, convert, order, orders_ext):
        return response_success()

    # TODO: REVIEW
    def prepare_reviews_import(self):
        return self

    def prepare_reviews_export(self):
        return self

    def get_reviews_main_export(self):
        id_src = self._notice['process']['reviews']['id_src']
        limit = self._notice['setting']['reviews']
        query = {
            'type': 'select',
            'query': "SELECT cm.*, p.post_type FROM _DBPRF_comments AS cm "
                     "LEFT JOIN _DBPRF_posts AS p ON p.ID = cm.comment_post_ID "
                     "WHERE p.post_type = 'product' AND cm.comment_ID > " + to_str(
                id_src) + " ORDER BY cm.comment_ID ASC LIMIT " + to_str(limit)
        }
        # reviews = self.get_connector_data(self.get_connector_url('query'), {'query': json.dumps(query)})
        reviews = self.select_data_connector(query, 'reviews')
        if not reviews or reviews['result'] != 'success':
            return response_error()
        return reviews

    def get_product_download_data(self, product_id):
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_postmeta WHERE meta_key = '_downloadable_files' AND post_id = " + to_str(
                product_id)
        }
        products = self.select_data_connector(query, 'products')
        if not products or products['result'] != 'success' or len(products['data']) == 0:
            return None
        return php_unserialize(products['data'][0]['meta_value'])

    def get_download_data(self, product_id):
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id = " + to_str(product_id)
        }
        products = self.select_data_connector(query, 'products')
        if not products or products['result'] != 'success' or len(products['data']) == 0:
            return None
        download_data = dict()
        for data in products['data']:
            if data['meta_key'] in ['_download_expiry', '_download_limit']:
                download_data[data['meta_key']] = data['meta_value'] if to_int(data['meta_value']) > 0 else None
        return download_data

    def get_reviews_ext_export(self, reviews):
        url_query = self.get_connector_url('query')
        reviews_ids = duplicate_field_value_from_list(reviews['data'], 'comment_ID')
        product_ids = duplicate_field_value_from_list(reviews['data'], 'comment_post_ID')
        review_ext_queries = {
            'comment_meta': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_commentmeta WHERE comment_id IN " + self.list_to_in_condition(
                    reviews_ids),
            },
            'product_info': {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_posts WHERE ID IN " + self.list_to_in_condition(product_ids),
            }
        }
        # reviews_ext = self.get_connector_data(url_query, {'serialize': True, 'query': json.dumps(review_ext_queries)})
        reviews_ext = self.select_multiple_data_connector(review_ext_queries, 'reviews')
        if not reviews_ext or reviews_ext['result'] != 'success':
            return response_error()
        return reviews_ext

    def convert_review_export(self, review, reviews_ext):
        review_data = self.construct_review()
        # review_data = self.add(review_data)
        review_data['id'] = review['comment_ID']
        product_info = get_row_from_list_by_field(reviews_ext['data']['product_info'], 'ID', review['comment_post_ID'])
        review_data['product']['id'] = review['comment_post_ID']
        if product_info:
            review_data['product']['code'] = product_info['post_name']
            review_data['product']['name'] = product_info['post_title']
        review_data['customer']['id'] = review['user_id']
        review_data['customer']['code'] = review['comment_author_email']
        review_data['customer']['name'] = review['comment_author']
        review_data['title'] = ''
        review_data['content'] = review['comment_content']
        rv_status = {
            '0': 2,  # pending
            '1': 1,  # approved
            'spam': 3  # not approved
        }
        review_data['status'] = rv_status.get(to_str(review['comment_approved']), 'spam')
        review_data['created_at'] = convert_format_time(review['comment_date'])
        review_data['updated_at'] = convert_format_time(review['comment_date'])

        rating = self.construct_review_rating()
        review_meta = get_list_from_list_by_field(reviews_ext['data']['comment_meta'], 'comment_id',
                                                  review['comment_ID'])
        rating['id'] = get_row_value_from_list_by_field(review_meta, 'comment_id', review['comment_ID'], 'meta_id')
        rating['rate_code'] = 'default'
        rating['rate'] = self.get_value_metadata(review_meta, 'rating', 5)
        review_data['rating'].append(rating)
        return response_success(review_data)

    def get_review_id_import(self, convert, review, reviews_ext):
        return review['comment_ID']

    def check_review_import(self, convert, review, reviews_ext):
        return True if self.get_map_field_by_src(self.TYPE_REVIEW, convert['id'], convert['code']) else False

    def router_review_import(self, convert, review, reviews_ext):
        return response_success('review_import')

    def before_review_import(self, convert, review, reviews_ext):
        return response_success()

    def review_import(self, convert, review, reviews_ext):
        lang_code = self._notice['target']['language_default']
        if convert.get('store_id'):
            lang_code = self._notice['map']['languages'].get(to_str(convert['store_id']))
        product_id = False
        if convert['product']['id'] or convert['product']['code']:
            if self.is_wpml():
                product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, convert['product']['id'],
                                                       convert['product']['code'], lang=lang_code)
            else:
                product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, convert['product']['id'],
                                                       convert['product']['code'])
            if not product_id:
                product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, None, convert['product']['code'],
                                                       lang=lang_code)
            if not product_id:
                msg = self.warning_import_entity('Review', convert['id'], convert['code'],
                                                 'product of review not exists.')
                return response_error(msg)
        customer_id = 0
        if convert['customer']['id'] or convert['customer']['code']:
            customer_id = self.get_map_field_by_src(self.TYPE_CUSTOMER, convert['customer']['id'])
            if not customer_id:
                customer_id = 0
        rv_status = {
            '2': 0,  # pedding
            '1': 1,  # approved
            '3': 'spam',  # not approved
            '0': 0
        }
        review_data = {
            'comment_post_ID': product_id,
            'comment_author': convert['customer']['name'],
            'comment_author_email': '',
            'comment_date': convert.get('created_at') if convert.get('created_at') else get_current_time(),
            'comment_date_gmt': convert['updated_at'] if convert['updated_at'] is not None else get_current_time(),
            'comment_content': convert['content'] if convert['content'] else '',
            'comment_karma': 0,
            'comment_approved': rv_status.get(str(convert['status']), 'spam'),
            'comment_parent': 0,
            'comment_type': "review",
            'user_id': customer_id
        }

        review_query = self.create_insert_query_connector("comments", review_data)
        review_id = self.import_review_data_connector(review_query, True, convert['id'])
        if not review_id:
            msg = self.warning_import_entity('Review', convert['id'], convert['code'])
            return response_error(msg)

        self.insert_map(self.TYPE_REVIEW, convert['id'], review_id, convert['code'])
        return response_success(review_id)

    def after_review_import(self, review_id, convert, review, reviews_ext):
        ratings = convert['rating']
        for rating in ratings:
            comment_meta = {
                'rating': to_int(rating['rate'])
            }
            for meta_key, meta_value in comment_meta.items():
                meta_insert = {
                    'comment_id': review_id,
                    'meta_key': meta_key,
                    'meta_value': meta_value
                }
                meta_query = self.create_insert_query_connector("commentmeta", meta_insert)
                self.import_data_connector(meta_query, 'review')
        return response_success()

    def addition_review_import(self, convert, review, reviews_ext):
        return response_success()

    # TODO: Page
    def check_page_import(self, convert, page, pages_ext):
        return True if self.get_map_field_by_src(self.TYPE_PAGE, convert['id'], convert['code'],
                                                 lang=self._notice['target']['language_default']) else False

    def page_import(self, convert, page, pages_ext):
        language_code = convert.get('language_code')
        if self.is_wpml() and not language_code:
            language_code = self._notice['target']['language_default']

        code_name = convert['title']
        code_name = self.sanitize_title(code_name).strip('-')
        if self.is_wpml() and language_code:
            code_name = code_name + '-' + language_code
        check_slug_exist = True
        while check_slug_exist:
            check_slug_exist = True if self.select_map(self._migration_id, self.TYPE_PAGE, None, None, None, code_name,
                                                       None, language_code) else False
            if check_slug_exist:
                code_name += to_str(get_value_by_key_in_dict(convert, 'id', ''))
        parent_id = self.get_map_field_by_src(self.TYPE_PAGE, to_int(convert['parent_id']), None, language_code)
        if not parent_id:
            parent_id = 0
        data = {
            'post_author': 1,
            'post_date': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_date_gmt': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_content': self.change_img_src_in_text(convert['content']) if convert['content'] else "",
            'post_title': convert['title'],
            'post_status': 'publish' if convert['status'] else 'trash',
            'comment_status': convert.get('comment_status', 'open'),
            'ping_status': 'open',
            'post_name': code_name[:200],
            'post_modified': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_modified_gmt': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_parent': parent_id,
            'post_type': 'page',
            'comment_count': 0,
            'guid': '',
            'post_excerpt': '',
            'to_ping': '',
            'pinged': '',
            'post_content_filtered': '',
            'menu_order': get_value_by_key_in_dict(convert, 'sort_order', 0)
        }
        page_query = self.create_insert_query_connector('posts', data)
        page_id = self.import_page_data_connector(page_query, True, convert['id'])
        if not page_id:
            return response_error('Page ' + to_str(convert['id']) + ' import false.')
        self.insert_map(self.TYPE_PAGE, convert['id'], page_id, convert['title'], code_name, None, language_code)
        return response_success(page_id)

    def after_page_import(self, page_id, convert, page, pages_ext):
        # data = {
        # 	'guid': self._notice['target']['cart_url'] + '?p=' + str(page_id)
        # }
        # where_id = {
        # 	'id': page_id
        # }
        # update_query = self.create_update_query_connector('posts', data, where_id)
        # self.import_data_connector(update_query, 'page')
        # data_meta = {
        # 	'post_id': page_id,
        # 	'meta_key': '_edit_lock',
        # 	'meta_value': int(time.time()),
        # }
        # self.import_page_data_connector(self.create_insert_query_connector('postmeta', data_meta), True, convert['id'])
        # thumbnail_id = False
        # if convert['images']:
        # 	for image in convert['images']:
        # 		image_process = self.process_image_before_import(image['url'], image.get('path', ''))
        # 		image_import_path = self.uploadImageConnector(image_process, self.add_prefix_path(self.make_woocommerce_image_path(image_process['path']), self._notice['target']['config']['image_product'].rstrip('/')))
        # 		if image_import_path:
        # 			product_image = self.remove_prefix_path(image_import_path, self._notice['target']['config']['image_product'])
        # 			image_details = self.get_sizes(image_process['url'])
        # 			thumbnail_id = self.wp_image(product_image, image_details)
        # 		postmeta = dict()
        # 		if thumbnail_id:
        # 			postmeta['_thumbnail_id'] = thumbnail_id
        # 		for meta_key, value in postmeta.items():
        # 			postmeta_data = {
        # 				'post_id': page_id,
        # 				'meta_key': meta_key,
        # 				'meta_value': value
        # 			}
        # 			self.import_page_data_connector(self.create_insert_query_connector('postmeta', postmeta_data), True, convert['id'])
        # data_revision = {
        # 	'post_author': 1,
        # 	'post_date': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert['created_at'] else get_current_time(),
        # 	'post_date_gmt': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert['created_at'] else get_current_time(),
        # 	'post_content': convert['content'],
        # 	'post_title': convert['title'],
        # 	'post_status': 'inherit',
        # 	'comment_status': 'closed',
        # 	'ping_status': 'closed',
        # 	'post_name': str(page_id) + '-revision-v1',
        # 	'post_modified': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert['created_at'] else get_current_time(),
        # 	'post_modified_gmt': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert['created_at'] else get_current_time(),
        # 	'post_parent': page_id,
        # 	'menu_order': get_value_by_key_in_dict(convert, 'sort_order', 0),
        # 	'post_type': 'revision',
        # 	'comment_count': 0,
        # 	'guid': self._notice['target']['cart_url'] + '/2019/08/27/' + str(page_id) + '-revision-v1',
        # 	'post_excerpt': '',
        # 	'to_ping': '',
        # 	'pinged': '',
        # 	'post_content_filtered': ''
        # }
        # self.import_page_data_connector(self.create_insert_query_connector('posts', data_revision), True, convert['id'])
        super().after_page_import(page_id, convert, page, pages_ext)
        if self.is_wpml():
            source_language_code = self._notice['target']['language_default']
            language_code = convert.get('language_code')
            if not language_code:
                language_code = source_language_code
                source_language_code = None
            trid = convert.get('trid')
            if not trid:
                trid = self.get_new_trid()
            wpml_default = {
                'element_type': 'post_page',
                'element_id': page_id,
                'trid': trid,
                'language_code': language_code,
                'source_language_code': source_language_code
            }
            self.import_data_connector(self.create_insert_query_connector("icl_translations", wpml_default), 'page')
            if not convert.get('language_code'):
                list_target_id = list()
                for src_language_id, target_language_id in self._notice['map']['languages'].items():
                    if target_language_id in list_target_id or to_str(target_language_id) == to_str(
                            self._notice['target']['language_default']):
                        continue
                    list_target_id.append(target_language_id)
                    page_lang = self.get_convert_data_language(convert, src_language_id)
                    page_lang['trid'] = trid
                    page_lang['language_code'] = target_language_id
                    page_import = self.page_import(page_lang, page, pages_ext)
                    if page_import['result'] == 'success':
                        self.after_page_import(page_import['data'], page_lang, page, pages_ext)

        return response_success()

    # TODO: Coupon
    def prepare_coupons_import(self):
        return response_success()

    def prepare_coupons_export(self):
        return self

    def get_coupons_main_export(self):
        id_src = self._notice['process']['coupons']['id_src']
        limit = self._notice['setting']['coupons']

        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_posts WHERE ID > " + to_str(
                id_src) + "  AND post_type = 'shop_coupon' ORDER BY ID ASC LIMIT " + to_str(limit),
        }
        coupons = self.select_data_connector(query, 'coupons')
        if not coupons or coupons['result'] != 'success':
            return response_error()
        return coupons

    def get_coupons_ext_export(self, coupons):
        coupon_ids = duplicate_field_value_from_list(coupons['data'], 'ID')
        coupon_id_con = self.list_to_in_condition(coupon_ids)
        coupon_ext_queries = {
            'postmeta': {
                'type': "select",
                'query': "SELECT * FROM _DBPRF_postmeta WHERE post_id IN " + coupon_id_con
            },
        }
        coupons_ext = self.select_multiple_data_connector(coupon_ext_queries, 'products')
        if (not coupons_ext) or coupons_ext['result'] != 'success':
            return response_error()
        return coupons_ext

    def convert_coupon_export(self, coupon, coupons_ext):
        coupon_data = self.construct_coupon()
        coupon_data['id'] = coupon['ID']
        postmeta = get_list_from_list_by_field(coupons_ext['data']['postmeta'], 'post_id', coupon['ID'])
        coupon_data['code'] = coupon['post_title']
        coupon_data['title'] = coupon['post_name']
        coupon_data['description'] = coupon['post_excerpt']
        coupon_data['status'] = True if coupon['post_status'] == 'publish' else False
        coupon_data['created_at'] = convert_format_time(coupon['post_date'])
        coupon_data['updated_at'] = convert_format_time(coupon['post_modified'])
        coupon_data['to_date'] = convert_format_time(self.get_value_metadata(postmeta, 'date_expires'))
        if not coupon_data['to_date']:
            coupon_data['to_date'] = convert_format_time(self.get_value_metadata(postmeta, 'expiry_date'))
        coupon_data['min_spend'] = self.get_value_metadata(postmeta, 'minimum_amount') if to_str(
            self.get_value_metadata(postmeta, 'minimum_amount')) != 'None' else None
        coupon_data['max_spend'] = self.get_value_metadata(postmeta, 'maximum_amount') if to_str(
            self.get_value_metadata(postmeta, 'maximum_amount')) != 'None' else None
        coupon_data['times_used'] = self.get_value_metadata(postmeta, 'usage_count')
        coupon_data['usage_limit'] = self.get_value_metadata(postmeta, 'usage_limit', 0)
        coupon_data['discount_amount'] = self.get_value_metadata(postmeta, 'coupon_amount')
        coupon_data['usage_per_customer'] = self.get_value_metadata(postmeta, 'usage_limit_per_user')
        coupon_data['type'] = self.PERCENT if self.get_value_metadata(postmeta,
                                                                      'discount_type') == 'percent' else self.FIXED
        coupon_data['simple_free_shipping'] = 1 if self.get_value_metadata(postmeta, 'free_shipping') == 'yes' else 0
        coupon_data['limit_usage_to_x_items'] = self.get_value_metadata(postmeta, 'limit_usage_to_x_items')
        product_ids = self.get_value_metadata(postmeta, 'product_ids')
        if product_ids:
            coupon_data['products'] = to_str(product_ids).split(',')
        category_ids = self.get_value_metadata(postmeta, 'product_categories')
        if category_ids:
            category_ids = php_unserialize(category_ids)
            if category_ids:
                coupon_data['categories'] = category_ids

        return response_success(coupon_data)

    def get_coupon_id_import(self, convert, coupon, coupons_ext):
        return coupon['ID']

    def check_coupon_import(self, convert, coupon, coupons_ext):
        return True if self.get_map_field_by_src(self.TYPE_COUPON, convert['id'], convert['code']) else False

    def router_coupon_import(self, convert, coupon, coupons_ext):
        return response_success('coupon_import')

    def before_coupon_import(self, convert, coupon, coupons_ext):
        return response_success()

    def coupon_import(self, convert, coupon, coupons_ext):
        coupon_data = {
            'post_author': 1,
            'post_date': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_date_gmt': convert['created_at'] if convert['created_at'] and '0000-00-00' not in convert[
                'created_at'] else get_current_time(),
            'post_content': '',
            'post_title': convert['code'] if convert['code'] else convert['title'],
            'post_excerpt': self.change_img_src_in_text(get_value_by_key_in_dict(convert, 'description', '')),
            'post_status': "publish" if convert['status'] else "draft",
            'comment_status': 'open',
            'ping_status': 'closed',
            'post_password': '',
            'post_name': self.strip_html_tag(convert['title']),
            'to_ping': '',
            'pinged': '',
            'post_modified': convert['updated_at'] if convert and convert['updated_at'] and '0000-00-00' not in convert[
                'updated_at'] else get_current_time(),
            'post_modified_gmt': convert['updated_at'] if convert and convert['updated_at'] and '0000-00-00' not in
                                                          convert['updated_at'] else get_current_time(),
            'post_content_filtered': '',
            'post_parent': 0,
            'guid': self._notice['target']['cart_url'] + "/?post_type=shop_coupon&#038;p=",
            'menu_order': convert.get('menu_order', 0),
            'post_type': "shop_coupon",
            'post_mime_type': '',
            'comment_count': 0
        }
        coupon_query = self.create_insert_query_connector('posts', coupon_data)
        coupon_import = self.import_data_connector(coupon_query, 'coupons', convert['id'])
        if not coupon_import:
            return response_error()
        self.insert_map(self.TYPE_COUPON, convert['id'], coupon_import, convert['code'])
        return response_success(coupon_import)

    def after_coupon_import(self, coupon_id, convert, coupon, coupons_ext):
        all_queries = list()
        product_ids = convert.get('products')
        if product_ids:
            product_id_map_arr = list()
            for product_id in product_ids:
                map_product_id = self.get_map_field_by_src(self.TYPE_PRODUCT, product_id)
                if map_product_id and map_product_id not in product_id_map_arr:
                    product_id_map_arr.append(to_str(map_product_id))
            if product_id_map_arr:
                product_ids = ','.join(product_id_map_arr)
            else:
                product_ids = None

        category_ids = convert.get('categories')
        cate_id_map_arr = list()
        if category_ids:
            for category_id in category_ids:
                map_cate_id = self.get_map_field_by_src(self.TYPE_CATEGORY, category_id)
                if map_cate_id and map_cate_id not in cate_id_map_arr:
                    cate_id_map_arr.append(to_str(map_cate_id))
        # if product_id_map_arr:
        # 	product_ids = ','.join(cate_id_map_arr)
        # else:
        # 	product_ids = None

        coupon_meta = {
            'discount_type': 'percent' if convert['type'] == self.PERCENT else 'fixed_cart' if convert[
                                                                                                   'type'] == self.FIXED else 'fixed_product',
            'coupon_amount': convert['discount_amount'],
            'usage_limit': convert['usage_limit'],
            'usage_limit_per_user': convert['usage_per_customer'],
            'free_shipping': 'yes' if 'simple_free_shipping' in convert and to_str(
                to_int(convert['simple_free_shipping'])) == '1' else 'no',
            'usage_count': convert['times_used'],
            'date_expires': convert['to_date'] if (
                    convert['to_date'] and convert['to_date'] != '0000-00-00 00:00:00') else '',
            'minimum_amount': convert['min_spend'],
            'maximum_amount': convert['max_spend'],
            'product_ids': product_ids if product_ids else None,
            'product_categories': php_serialize(cate_id_map_arr) if cate_id_map_arr else '',
            'customer_email': php_serialize(convert.get('customer')),
            'limit_usage_to_x_items': convert.get('limit_usage_to_x_items', 0),
        }
        for meta_key, meta_value in coupon_meta.items():
            meta_insert = {
                'post_id': coupon_id,
                'meta_key': meta_key,
                'meta_value': str(meta_value).replace(')', '').replace(',', '').replace("'", '')
            }
            meta_query = self.create_insert_query_connector("postmeta", meta_insert)
            all_queries.append(meta_query)
        all_queries.append(self.create_update_query_connector('posts', {
            'guid': self._notice['target']['cart_url'] + "/?post_type=shop_coupon&#038;p=" + to_str(coupon_id)},
                                                              {'ID': coupon_id}))
        self.import_multiple_data_connector(all_queries, 'coupons')
        return response_success()

    def addition_coupon_import(self, convert, coupon, coupons_ext):
        return response_success()

    def display_finish_target(self):
        migration_id = self._migration_id
        recent_exist = self.select_row(TABLE_RECENT, {'migration_id': migration_id})
        notice = json.dumps(self._notice)
        if recent_exist:
            self.update_obj(TABLE_RECENT, {'notice': notice}, {'migration_id': migration_id})
        else:
            self.insert_obj(TABLE_RECENT, {'notice': notice, 'migration_id': migration_id})
        target_cart_type = self._notice['target']['cart_type']
        target_setup_type = self.target_cart_setup(target_cart_type)
        # if target_setup_type == 'connector':
        token = self._notice['target']['config']['token']
        url = self.get_connector_url('clearcache', token)
        self.get_connector_data(url)
        all_queries = list()
        all_queries.append({
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE option_name = 'product_cat_children'"
        })
        all_queries.append({
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE option_name = '_transient_wc_attribute_taxonomies'"
        })
        all_queries.append({
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE `option_name` LIKE '%_transient_timeout_wc_report_customers%'"
        })
        all_queries.append({
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE `option_name` LIKE '%_transient_wc_report_customers%'"
        })
        all_queries.append({
            'type': 'query',
            'query': "DELETE FROM `_DBPRF_options` WHERE option_name = 'urlrewrite_type'"
        })
        all_queries.append({
            'type': 'query',
            'query': "UPDATE `_DBPRF_posts` SET `comment_count`= (SELECT COUNT(comment_ID) FROM `_DBPRF_comments` WHERE `_DBPRF_comments`.comment_post_ID = `_DBPRF_posts`.ID AND `_DBPRF_comments`.comment_approved = 1) WHERE `post_type` IN ('product', 'post')"
        })
        all_queries.append({
            'type': 'query',
            'query': "UPDATE `_DBPRF_postmeta` SET `meta_value`= (SELECT COUNT(comment_ID) FROM `_DBPRF_comments` WHERE `_DBPRF_comments`.comment_post_ID = `_DBPRF_postmeta`.post_id AND `_DBPRF_comments`.comment_approved = 1) WHERE `meta_key` = '_wc_review_count'"
        })
        all_queries.append({
            'type': 'query',
            'query': "UPDATE `_DBPRF_postmeta` SET `meta_value`= (SELECT AVG(cmta.`meta_value`) FROM `_DBPRF_comments` AS cmt LEFT JOIN `_DBPRF_commentmeta` AS cmta ON cmt.`comment_ID` = cmta.`comment_ID` WHERE cmt.`comment_post_ID` = `_DBPRF_postmeta`.`post_id` AND cmt.comment_approved = 1 AND cmta.`meta_key` = 'rating') WHERE `meta_key` = '_wc_average_rating'"
        })
        # all_queries.append({
        # 	'type': 'query',
        # 	'query': "UPDATE `_DBPRF_term_taxonomy` tt "
        # 	         "SET tt.count = (SELECT COUNT( *) as total "
        # 	         "FROM _DBPRF_term_relationships r JOIN _DBPRF_posts p ON r.object_id = p.ID "
        # 	         "WHERE r.term_taxonomy_id = tt.term_taxonomy_id AND p.post_type = 'product' AND p.post_parent = '') "
        # 	         "WHERE tt.taxonomy IN('product_cat', 'product_type', 'product_tag', 'product_brand')"
        # })
        all_queries.append({
            'type': 'query',
            'query': "UPDATE `_DBPRF_term_taxonomy` AS tt SET tt.count = (SELECT COUNT(1) AS total FROM _DBPRF_term_relationships AS tr WHERE tt.term_taxonomy_id = tr.term_taxonomy_id AND tr.object_id IN (SELECT ID FROM _DBPRF_posts WHERE post_type = 'product'))"
        })
        clear_cache = self.import_multiple_data_connector(all_queries)
        option_data = {
            'option_name': 'urlrewrite_type',
            'option_value': 'urlrewrite',
            'autoload': 'yes'
        }
        if self._notice['support'].get('seo_301'):
            option_data = {
                'option_name': 'urlrewrite_type',
                'option_value': 'url301',
                'autoload': 'yes'
            }
        option_query = self.create_insert_query_connector('options', option_data)
        option_import = self.import_data_connector(option_query, 'options')
        return response_success()

    def substr_replace(self, subject, replace, start, length):  # attr_taxonomy, '', 0, 3)
        if length == None:
            return subject[:start] + replace
        elif length < 0:
            return subject[:start] + replace + subject[length:]
        else:
            return subject[:start] + replace + subject[start + length:]

    def add_construct_default(self, construct):
        construct['site_id'] = 1
        construct['language_id'] = self._notice['src']['language_default']
        return construct

    def get_term_by_name(self, data):
        query = {
            'type': 'select',
            'query': "SELECT * FROM _DBPRF_term_taxonomy AS tt "
                     "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tt.term_id "
                     "WHERE tt.taxonomy = 'product_visibility' AND t.name = '" + data + "'"
        }
        product_taxonomy = self.select_data_connector(query)
        if product_taxonomy['result'] == 'success' and product_taxonomy['data']:
            return product_taxonomy['data'][0]['term_taxonomy_id']
        return None

    def get_product_type(self, product_type):
        if not self.product_types:
            query = {
                'type': 'select',
                'query': "SELECT * FROM _DBPRF_term_taxonomy AS tt "
                         "LEFT JOIN _DBPRF_terms AS t ON t.term_id = tt.term_id "
                         "WHERE tt.taxonomy = 'product_type'"
            }
            product_types = self.select_data_connector(query)
            if product_types['result'] == 'success' and product_types['data']:
                for product_type_row in product_types['data']:
                    self.product_types[product_type_row['slug']] = product_type_row['term_taxonomy_id']

        return self.product_types.get(product_type, 2)

    def import_category_parent(self, convert_parent, lang_code=None):
        category_type = self.TYPE_CATEGORY
        if convert_parent.get('is_blog'):
            category_type = self.TYPE_CATEGORY_BLOG
        parent_exists = self.get_map_field_by_src(category_type, convert_parent['id'], convert_parent['code'],
                                                  lang_code)
        if parent_exists:
            return response_success(parent_exists)
        if self.is_wpml() and lang_code:
            convert_parent['language_code'] = lang_code
            for src_language_id, target_language_id in self._notice['map']['languages'].items():
                if to_str(lang_code) == to_str(target_language_id):
                    lang_data = convert_parent
                    if to_str(src_language_id) in convert_parent['languages'] and convert_parent['languages'][
                        to_str(src_language_id)]:
                        lang_data = convert_parent['languages'][to_str(src_language_id)]
                    convert_parent['name'] = lang_data['name']
                    convert_parent['description'] = lang_data['description']
                    convert_parent['short_description'] = lang_data['short_description']
                    convert_parent['meta_title'] = lang_data['meta_title']
                    convert_parent['meta_keyword'] = lang_data['meta_keyword']
                    convert_parent['meta_description'] = lang_data['meta_description']
                    convert_parent['url_key'] = lang_data.get('url_key', '')
        category = get_value_by_key_in_dict(convert_parent, 'category', dict())
        categories_ext = get_value_by_key_in_dict(convert_parent, 'categories_ext', dict())
        category_parent_import = self.category_import(convert_parent, category, categories_ext)
        self.after_category_import(category_parent_import['data'], convert_parent, category, categories_ext)
        return category_parent_import

    def get_list_from_list_by_field_as_first_key(self, list_data, field='', first_key=''):
        result = list()
        if isinstance(list_data, dict):
            for key, row in list_data.items():
                if field in row:
                    if row[field].find(first_key) == 0:
                        result.append(row)
        else:
            if field and to_str(field) != '':
                for row in list_data:
                    if field in row:
                        if row[field].find(first_key) == 0:
                            result.append(row)
            else:
                for row in list_data:
                    if row:
                        v_index = row.find(first_key)
                        if v_index == 0:
                            result.append(row)
        return result

    def process_image_before_import(self, url, path):
        if not path:
            full_url = url
            path = strip_domain_from_url(url)
        else:
            full_url = join_url_path(url, path)
        if path and path.find('/wp-content/uploads/') != -1:
            newpath = path.split('/wp-content/uploads/')
            if newpath and to_len(newpath) > 1:
                path = newpath[1]
        path = re.sub(r"[^a-zA-Z0-9.-_()]", '', path)
        full_url = self.parse_url(full_url)
        return {
            'url': full_url,
            'path': path
        }

    def wpml_attributes_to_in_condition(self, list_keys):
        if not list_keys:
            return "('null')"
        result = "('tax_" + "','tax_".join([str(k) for k in list_keys]) + "')"
        return result

    def brand_image_in_condition(self, term_ids):
        if not term_ids:
            return "('null')"
        result = "('brand_taxonomy_image" + "','brand_taxonomy_image".join([str(k) for k in term_ids]) + "')"
        return result

    def detect_seo(self):
        return 'default_seo'

    def categories_default_seo(self, category, categories_ext):
        result = list()
        seo_cate = self.construct_seo_category()
        seo_cate['request_path'] = self._notice['src']['config']['product_category_base'].strip('/') + '/' + to_str(
            category['slug'])
        seo_cate['default'] = True
        result.append(seo_cate)
        return result

    def products_default_seo(self, product, products_ext):
        result = list()
        if self._notice['src']['config']['product_base'].find('%product_cat%') != -1:
            term_relationship = get_list_from_list_by_field(products_ext['data']['term_relationship'], 'object_id',
                                                            product['ID'])
            category_src = get_list_from_list_by_field(term_relationship, 'taxonomy', 'product_cat')
            if category_src:
                for product_category in category_src:
                    seo_product = self.construct_seo_product()
                    seo_product['request_path'] = self._notice['src']['config']['product_base'].strip(
                        '/') + '/' + to_str(product_category['slug']) + '/' + to_str(product['post_name'])
                    seo_product['category_id'] = product_category['term_id']
                    result.append(seo_product)
        else:
            seo_product = self.construct_seo_product()
            seo_product['request_path'] = self._notice['src']['config']['product_base'].strip('/') + '/' + to_str(
                product['post_name'])
            seo_product['default'] = True
            result.append(seo_product)
        if product['post_name']:
            seo_product = self.construct_seo_product()
            seo_product['request_path'] = to_str(product['post_name'])
            seo_product['default'] = True
            result.append(seo_product)
        return result

    def get_order_status_label(self, order_status):
        if not order_status:
            return ''
        order_status = order_status.replace('wc-', '')
        order_status = order_status.replace('-', ' ')
        order_status = order_status.capitalize()
        return order_status

    def get_woo_attribute_id(self, pro_attr_code, attribute_name, language_code=None, language_attribute_data=None,
                             attribute_type='select'):
        # if to_str(pro_attr_code)[0:3] != 'pa_':
        #     pro_attr_code = "pa_" + pro_attr_code
        # if self.is_wpml() and language_code != self._notice['target']['language_default']:
        # 	attribute_data_default = self.get_convert_data_language(language_attribute_data, None, self._notice['target']['language_default'], 'option_languages')
        # 	option_lang_name = attribute_data_default.get('option_name')
        # 	if not option_lang_name:
        # 		option_lang_name = attribute_data_default.get('attribute_name')
        # 	if option_lang_name:
        pro_attr_code = urllib.parse.unquote(pro_attr_code)
        woo_attribute_id = self.get_map_field_by_src(self.TYPE_ATTR, None, 'pa_' + pro_attr_code)
        # if woo_attribute_id:
        # 	return woo_attribute_id
        if not woo_attribute_id:
            attribute_data = {
                'attribute_name': pro_attr_code,
                'attribute_type': attribute_type
            }
            attribute_result = self.select_data_connector(
                self.create_select_query_connector('woocommerce_attribute_taxonomies', attribute_data))
            woo_attribute_id = None
            if attribute_result and attribute_result['data']:
                woo_attribute_id = attribute_result['data'][0]['attribute_id']
            if not woo_attribute_id:
                pro_attr_data = {
                    'attribute_name': pro_attr_code,
                    'attribute_label': attribute_name,
                    'attribute_type': attribute_type,
                    'attribute_orderby': "menu_order",
                    'attribute_public': 0,
                }
                woo_attribute_id = self.import_data_connector(
                    self.create_insert_query_connector('woocommerce_attribute_taxonomies', pro_attr_data), 'products')
                if woo_attribute_id:
                    self.insert_map(self.TYPE_ATTR, None, woo_attribute_id, 'pa_' + pro_attr_code)

        if woo_attribute_id:
            if self.is_wpml():
                attribute_data_lang = self.get_convert_data_language(language_attribute_data, None, language_code,
                                                                     'option_languages')
                option_lang_name = attribute_data_lang.get('option_name')
                if not option_lang_name:
                    option_lang_name = attribute_data_lang.get('attribute_name')
                if option_lang_name != attribute_name:
                    translate_id = self.get_map_field_by_src('translate', woo_attribute_id, None, language_code)
                    if not translate_id:
                        translate_query = {
                            'icl_strings': self.create_select_query_connector('icl_strings', {'value': attribute_name,
                                                                                              'name': 'taxonomy singular name: ' + attribute_name}),
                            'icl_string_translations': {
                                'type': 'select',
                                'query': "select * from _DBPRF_icl_string_translations where string_id in (" +
                                         self.create_select_query_connector('icl_strings', {'value': attribute_name,
                                                                                            'name': 'taxonomy singular name: ' + attribute_name},
                                                                            'id')['query'] + ")"
                            }
                        }
                        select = self.select_multiple_data_connector(translate_query)
                        if select['result'] == 'success':
                            icl_string_id = None
                            is_tranlate = False
                            if not select['data']['icl_strings']:
                                icl_strings_data = {
                                    'language': self._notice['target']['language_default'],
                                    'context': 'WordPress',
                                    'name': 'taxonomy singular name: ' + attribute_name,
                                    'value': attribute_name,
                                    'string_package_id': None,
                                    'wrap_tag': '',
                                    'type': 'LINE',
                                    'title': None,
                                    'status': 2,
                                    'gettext_context': '',
                                    'domain_name_context_md5': hashlib.md5(
                                        to_str('WordPresstaxonomy singular name: ' + attribute_name).encode()),
                                    'translation_priority': 'optional',
                                    'word_count': None
                                }
                                icl_string_id = self.import_product_data_connector(
                                    self.create_insert_query_connector('icl_strings', icl_strings_data))

                            else:
                                icl_string = select['data']['icl_strings'][0]
                                if icl_string['language'] != language_code:
                                    icl_string_id = icl_string['id']
                                    check = get_row_from_list_by_field(select['data']['icl_string_translations'],
                                                                       'language', language_code)
                                    is_tranlate = True if check else False
                                else:
                                    is_tranlate = True
                            if icl_string_id and not is_tranlate:
                                icl_string_translations_data = {
                                    'string_id': icl_string_id,
                                    'language': language_code,
                                    'status': 10,
                                    'value': option_lang_name,
                                    'translator_id': None,
                                    'translation_service': '',
                                    'batch_id': 0,
                                    'translation_date': get_current_time()
                                }
                                icl_string_translation_id = self.import_product_data_connector(
                                    self.create_insert_query_connector('icl_string_translations',
                                                                       icl_string_translations_data))
                                if icl_string_translation_id:
                                    self.insert_map('translate', woo_attribute_id, icl_string_translation_id, None,
                                                    None, None, language_code)
        return woo_attribute_id

    def get_woo_attribute_value(self, attribute_value, pro_attr_code, language_code=None, attribute_data=None, desc=''):
        pro_attr_code = urllib.parse.unquote(pro_attr_code)
        if self.is_wpml():
            value_data = self.get_convert_data_language(attribute_data, None, language_code, 'option_value_languages')
            if value_data:
                attribute_value = value_data['option_value_name']
        attribute_value = to_str(attribute_value)[:200]
        slug_default = self.get_slug_attr(attribute_data)
        slug = self.get_slug_attr(attribute_data, language_code)
        opt_value_id = None
        opt_value_exist = self.select_map(self._migration_id, self.TYPE_ATTR_VALUE, None, None, 'pa_' + pro_attr_code,
                                          None, slug, language_code)
        if opt_value_exist:
            if not self.is_wpml() or not language_code or language_code == self._notice['target']['language_default']:
                return opt_value_exist['id_desc']
            else:
                opt_value_id = opt_value_exist['id_desc']

        if not opt_value_id:
            if self.is_wpml() and language_code != self._notice['target']['language_default']:
                new_slug = slug_default + '-' + to_str(language_code) if slug == slug_default else slug
            else:
                new_slug = slug_default
            value_term = {
                'name': attribute_value,
                'slug': new_slug,
                'term_group': 0,
            }
            term_id = self.import_product_data_connector(self.create_insert_query_connector('terms', value_term),
                                                         'products')
            value_term_taxonomy = {
                'term_id': term_id,
                'taxonomy': 'pa_' + pro_attr_code,
                'description': desc,
                'parent': 0,
                'count': 0
            }
            opt_value_id = self.import_product_data_connector(
                self.create_insert_query_connector('term_taxonomy', value_term_taxonomy), 'products')
        if opt_value_id:
            self.insert_map(self.TYPE_ATTR_VALUE, None, opt_value_id, 'pa_' + pro_attr_code, None, slug,
                            language_code)
            if self.is_wpml():
                attribute_data_lang = self.get_convert_data_language(attribute_data, None, language_code,
                                                                     'option_value_languages')

                if self.is_wpml() and language_code != self._notice['target']['language_default']:
                    new_slug = slug_default + '-' + to_str(language_code) if slug == slug_default else slug
                else:
                    new_slug = slug_default

                query_check_term = {
                    'type': 'select',
                    'query': 'SELECT * FROM _DBPRF_terms AS term LEFT JOIN _DBPRF_term_taxonomy AS taxonomy ON term.term_id = taxonomy.term_id WHERE term.slug IN ' + self.list_to_in_condition(
                        [new_slug, slug_default]) + ' AND  term.name = ' + self.escape(
                        attribute_data_lang['option_value_name']) + " AND taxonomy.taxonomy = " + self.escape(
                        'pa_' + pro_attr_code)
                }
                term_data = self.select_data_connector(query_check_term, 'check_slug_lang')
                option_value_default = get_row_value_from_list_by_field(term_data, 'slug', slug_default, 'term_id')
                translate_query = {
                    'icl_translations': {
                        'type': 'select',
                        'query': 'select * from _DBPRF_icl_translations where trid in (select trid from _DBPRF_icl_translations where  ' + self.dict_to_where_condition(
                            {'element_id': opt_value_id, 'element_type': 'tax_pa_' + pro_attr_code}) + ')'
                    },

                }
                select = self.select_multiple_data_connector(translate_query)
                self.log(select, 'data_select')
                if select['result'] == 'success':
                    trid = None
                    is_tranlate = False
                    if not select['data']['icl_translations'] and language_code == self._notice['target'][
                        'language_default']:
                        trid = self.get_new_trid()
                        icl_translations_data = {
                            'language_code': self._notice['target']['language_default'],
                            'element_type': 'tax_pa_' + pro_attr_code,
                            'element_id': opt_value_id,
                            'trid': trid,
                            'source_language_code': None,
                        }
                        icl_translation_id = self.import_product_data_connector(
                            self.create_insert_query_connector('icl_translations', icl_translations_data))
                    else:
                        term_id_default = self.select_map(self._migration_id, self.TYPE_ATTR_VALUE, None, None,
                                                          'pa_' + pro_attr_code, None, slug_default,
                                                          self._notice['target']['language_default'])
                        self.log(term_id_default, 'term_id_default')
                        opt_value_id_default = term_id_default['id_desc']
                        query_check_trans = {
                            'type': 'select',
                            'query': 'SELECT * FROM _DBPRF_icl_translations WHERE  ' + self.dict_to_where_condition(
                                {'element_type': 'tax_pa_' + pro_attr_code})
                        }
                        select = self.select_data_connector(query_check_trans, 'check_trans')
                        icl_translations = get_row_from_list_by_field(select['data'], 'element_id',
                                                                      opt_value_id_default)
                        trid = icl_translations['trid']
                        check = get_row_from_list_by_field(select['data'], 'element_id', opt_value_id)
                        is_tranlate = True if check else False
                    if trid and not is_tranlate:

                        icl_translations_data = {
                            'language_code': language_code,
                            'element_type': 'tax_pa_' + pro_attr_code,
                            'element_id': opt_value_id,
                            'trid': trid,
                            'source_language_code': self._notice['target']['language_default'],
                        }
                        self.import_product_data_connector(
                            self.create_insert_query_connector('icl_translations', icl_translations_data))

        return opt_value_id

    def to_timestamp(self, value, str_format='%Y-%m-%d %H:%M:%S'):
        try:
            timestamp = to_int(time.mktime(time.strptime(value, str_format)))
            if timestamp:
                return timestamp
            return to_int(time.time())
        except:
            return to_int(time.time())

    def get_map_field_by_src(self, map_type=None, id_src=None, code_src=None, lang=None, field='id_desc'):
        if not self.is_wpml() and not self.is_polylang() or map_type in [self.TYPE_PATH_IMAGE, self.TYPE_IMAGE]:
            return super().get_map_field_by_src(map_type, id_src, code_src, field)
        if not id_src and not code_src:
            return False
        _migration_id = self._migration_id
        # if id_src:
        # 	code_src = None
        # else:
        # 	code_src = None
        map_data = self.select_map(_migration_id, map_type, id_src, None, code_src, None, None, lang)
        if not map_data:
            return False
        return map_data.get(field, False)

    def select_map(self, _migration_id=None, map_type=None, id_src=None, id_desc=None, code_src=None, code_desc=None,
                   value=None, lang=None):
        if not self.is_wpml() and not self.is_polylang() or map_type in [self.TYPE_PATH_IMAGE, self.TYPE_IMAGE]:
            return super().select_map(_migration_id, map_type, id_src, id_desc, code_src, code_desc, value)
        where = dict()
        if _migration_id:
            where['migration_id'] = _migration_id
            if self._datasync_migration_id:
                where['migration_id'] = self._datasync_migration_id
        if map_type:
            where['type'] = map_type
        if id_src:
            where['id_src'] = id_src
        if id_desc:
            where['id_desc'] = id_desc
        if code_src:
            where['code_src'] = code_src
        if code_desc:
            where['code_desc'] = code_desc
        if value:
            where['value'] = value
        if (self.is_wpml() or self.is_polylang()) and map_type in [self.TYPE_CATEGORY, self.TYPE_PRODUCT,
                                                                   self.TYPE_ATTR, self.TYPE_ATTR_VALUE]:
            where['lang'] = lang
        if not where:
            return None
        result = self.select_obj(TABLE_MAP, where)
        try:
            data = result['data'][0]
        except Exception as e:
            data = None
        return data

    def insert_map(self, map_type=None, id_src=None, id_desc=None, code_src=None, code_desc=None, value=None,
                   lang=None):
        if to_int(id_src) == 0 and to_str(id_src) != '0':
            id_src = None
        if self._sync_import and map_type:
            map_type = "sync_{}".format(map_type)
        data_inset = {
            'migration_id': self._migration_id,
            'type': map_type,
            'id_src': id_src,
            'code_src': code_src,
            'id_desc': id_desc,
            'code_desc': code_desc,
            'value': value,
        }
        if self.is_wpml() or self.is_polylang():
            data_inset['lang'] = lang
        insert = self.insert_obj(TABLE_MAP, data_inset)
        if (not insert) or (insert['result'] != 'success'):
            return False
        return insert['data']

    def is_wpml(self):
        return self._notice[self.get_type()]['support'].get('wpml')

    def is_polylang(self):
        return self._notice[self.get_type()]['support'].get('polylang')

    def get_convert_data_language(self, convert, src_language_id=None, target_language_id=None,
                                  key_language='languages'):
        if not self.is_wpml() and not self.is_polylang():
            return convert
        list_language_data = convert.get(key_language)
        if not list_language_data:
            return convert
        language_data = None
        if src_language_id:
            if list_language_data.get(to_str(src_language_id)):
                language_data = list_language_data[to_str(src_language_id)]
        elif target_language_id:
            for src_id, data in list_language_data.items():
                if self._notice['map']['languages'].get(to_str(src_id)) == target_language_id:
                    language_data = data
                    break
        if not language_data:
            return convert
        for key_lang, value in language_data.items():
            if not value:
                continue
            if key_lang == 'option_value_name' and convert.get(
                    'option_type') == self.OPTION_MULTISELECT and 'position_option' in convert:
                value_lang = to_str(value).split(';')
                if len(value_lang) > to_int(convert.get('position_option')):
                    value = value_lang[to_int(convert.get('position_option'))]
            convert[key_lang] = value
        return convert

    def get_pro_attr_code_default(self, option):
        if self.is_wpml():
            option = self.get_convert_data_language(option, None, self._notice['target']['language_default'],
                                                    'option_languages')
        pro_attr_code = to_str(option['option_name']).lower()
        # attribute_name = option['option_name']
        pro_attr_code = pro_attr_code.replace(' ', '_')
        if option['option_code']:
            pro_attr_code = to_str(option['option_code']).lower()
            pro_attr_code = pro_attr_code.replace(' ', '_')
        pro_attr_code_len = 28
        check_encode = chardet.detect(pro_attr_code.encode())
        if check_encode['encoding'] != 'ascii':
            pro_attr_code = pro_attr_code[0:14]
            pro_attr_code_len = 200
        pro_attr_code = self.sanitize_title(pro_attr_code, pro_attr_code_len)
        return pro_attr_code

    def get_slug_attr(self, option_value, language_code=None):
        if option_value['option_value_code']:
            return self.sanitize_title(to_str(option_value['option_value_code'])).lower()
        attribute_value = option_value['option_value_name']
        if self.is_wpml():
            if not language_code:
                language_code = self._notice['target']['language_default']
            value_data = self.get_convert_data_language(option_value, None, language_code, 'option_value_languages')
            if value_data:
                attribute_value = value_data['option_value_name']
        return self.sanitize_title(to_str(attribute_value).lower())

    def get_key_check_default(self, attributes):
        key_check = ''
        for children_attribute in attributes:
            if self.is_wpml():
                children_attribute = self.get_convert_data_language(children_attribute, None,
                                                                    self._notice['target']['language_default'],
                                                                    'option_value_languages')
            if key_check:
                key_check += '|'
            key_check += to_str(children_attribute['option_name']) + ':' + to_str(
                children_attribute['option_value_name'])
        return key_check

    def lecm_rewrite_table_construct(self):
        return {
            'table': '_DBPRF_lecm_rewrite',
            'rows': {
                'id': 'INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY',
                'link': 'VARCHAR(255)',
                'type': 'VARCHAR(255)',
                'type_id': 'INT(11)',
                'redirect_type': 'SMALLINT(5)',
            },
        }

    def is_woo2woo(self):
        return self._notice['src']['cart_type'] == self._notice['target']['cart_type']

    def check_sync_child(self, child, combination, check_any=False):
        for attribute in combination:
            if not check_any:
                if to_str(child.get(attribute['option_name'])) != to_str(attribute['option_value_name']):
                    if to_str(child.get(to_str(attribute['option_code']).replace(' ', '-'))) != to_str(
                            attribute['option_value_name']) and to_str(child.get(
                        to_str(attribute['option_code']).replace(' ', '-').replace('/', '-').replace('---',
                                                                                                     '-'))) != to_str(
                        attribute['option_value_name']):
                        return False
            elif to_str(child.get(attribute['option_name'])) or to_str(
                    child.get(to_str(attribute['option_code']).replace(' ', '-'))):
                if to_str(child.get(to_str(attribute['option_code']).replace(' ', '-'))) != to_str(
                        attribute['option_value_name']):
                    return False
        return True

    def select_all_category_map(self):
        where = dict()
        where['migration_id'] = self._migration_id
        if self._datasync_migration_id:
            where['migration_id'] = self._datasync_migration_id
        where['type'] = self.TYPE_CATEGORY if not self.blog_running else self.TYPE_CATEGORY_BLOG
        result = self.select_obj(TABLE_MAP, where)
        data = list()
        if result['result'] == 'success' and result['data']:
            data = result['data']

        result_data = list()
        if data:
            for row in data:
                value = row['id_desc']
                result_data.append(value)

        return result_data

    def create_file_variant_limit(self):
        file_path = get_pub_path() + '/media/' + to_str(self._migration_id)
        if not os.path.exists(file_path):
            os.makedirs(file_path, mode=0o777)
        file_name = file_path + '/variants.csv'
        column = ['src_id', 'target_id', 'name', 'sku', 'variants']
        with open(file_name, mode='a') as employee_file:
            employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            employee_writer.writerow(column)
        return

    def warning_variant_limit(self, convert):
        if convert['id']:
            product = "#" + to_str(convert['id'])
        else:
            product = ': ' + to_str(convert['code'])
        self.sleep_time(0, 'variant', True, msg=product)

    def log_variant_limit(self, product_id, convert, variants):
        self.is_variant_limit = True
        file_name = get_pub_path() + '/media/' + to_str(self._migration_id) + '/variants.csv'
        if not os.path.isfile(file_name):
            self.create_file_variant_limit()
        column = [convert['id'] if convert['id'] else convert['code'], product_id, convert['name'], convert['sku'],
                  variants]

        with open(file_name, mode='a') as employee_file:
            employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            employee_writer.writerow(column)
        return

    def check_slug_exist(self, slug=None):
        select = {
            'slug': slug,
        }
        category_data = self.select_data_connector(self.create_select_query_connector('terms', select))

        try:
            term_id = category_data['data'][0]['term_id']
        except Exception:
            term_id = False
        return term_id

    def rf_check_category_slug_exist(self, slug=None):
        """
        Query Database and return category id base on slug.

        Return: category_id or False
        """
        query = {
            'type': 'select',
            'query': "SELECT a.term_id,b.term_taxonomy_id, a.name, b.taxonomy, b.description, a.slug, a.term_group "
                     "from _DBPRF_terms as a INNER JOIN _DBPRF_term_taxonomy as b "
                     "ON a.term_id = b.term_id "
                     "WHERE b.taxonomy ='product_cat' "
                     "AND a.slug = " + self.escape(slug)
        }
        category_data = self.select_data_connector(query, 'category_data')
        try:
            term_id = category_data['data'][0]['term_id']
        except Exception:
            term_id = False
        return term_id

    def get_query_img_wpml(self, img_id, language_code):
        source_language_code = self._notice['target']['language_default']
        default_language_code = language_code
        if source_language_code == default_language_code:
            default_language_code = source_language_code
            source_language_code = None
        trid = self.get_new_trid()
        wpml_img_data = {
            'element_type': 'post_attachment',
            'element_id': img_id,
            'trid': trid,
            'language_code': default_language_code,
            'source_language_code': source_language_code
        }
        wpml_img_query = self.create_insert_query_connector("icl_translations", wpml_img_data)
        return wpml_img_query

    def rf_get_query_img_wpml(self, img_id, language_code, trid):
        source_language_code = self._notice['target']['language_default']
        default_language_code = language_code
        if source_language_code == default_language_code:
            default_language_code = source_language_code
            source_language_code = None
        wpml_img_data = {
            'element_type': 'post_attachment',
            'element_id': img_id,
            'trid': trid,
            'language_code': default_language_code,
            'source_language_code': source_language_code
        }
        wpml_img_query = self.create_insert_query_connector("icl_translations", wpml_img_data)
        return wpml_img_query

    def check_exist_code_product(self, code_product):
        check = self.select_data_connector(self.create_select_query_connector('posts', {'posttype'}))

    def _get_customer_lookup_id(self, user_id):
        if not user_id:
            return 0
        select = {
            'user_id': user_id,
        }
        customer_lookup_data = self.select_data_connector(
            self.create_select_query_connector('wc_customer_lookup', select))

        try:
            customer_lookup_id = customer_lookup_data['data'][0]['customer_id']
        except Exception:
            customer_lookup_id = 0
        return customer_lookup_id
