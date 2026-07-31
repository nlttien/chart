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
    return fetch('https://api.qiandao.com/c2c-web/v1/common/query-config', {
        method: 'POST',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify({"spuId":"836104794648117776","scene":"CURRENCY_SPU_PAGE_BOTTOM_BUY"})
    }).then(res => res.json()).catch(err => err.toString());
    """
    res = page.run_js(js)
    print("Fetch result:", res)
    
    page.quit()
except Exception as e:
    print("ERROR:", e)
