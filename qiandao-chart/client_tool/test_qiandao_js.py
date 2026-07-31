from DrissionPage import ChromiumOptions, ChromiumPage
import time

try:
    co = ChromiumOptions()
    co.auto_port()
    co.set_argument('--headless')
    page = ChromiumPage(co)
    page.get('https://qiandao.com')
    time.sleep(3)
    
    js = """
    let keys = Object.keys(window);
    let api_clients = keys.filter(k => k.toLowerCase().includes('axios') || k.toLowerCase().includes('api') || k.toLowerCase().includes('http') || k.toLowerCase().includes('request') || k.toLowerCase().includes('fetch'));
    return api_clients;
    """
    res = page.run_js(js)
    print("Found potential API clients:", res)
    
    js2 = """
    return typeof window.$nuxt !== 'undefined';
    """
    is_nuxt = page.run_js(js2)
    print("Is Nuxt?", is_nuxt)
    
    page.quit()
except Exception as e:
    print("ERROR:", e)
