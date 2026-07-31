from DrissionPage import ChromiumOptions, ChromiumPage
import time

try:
    co = ChromiumOptions()
    co.auto_port()
    co.set_argument('--headless')
    page = ChromiumPage(co)
    page.listen.start('currency-spu-price-list')
    url = "https://qiandao.com/currency/currency-zone?catalogName=%E6%B5%81%E6%94%BE2%E4%B8%93%E5%8C%BA&tagIds=[1707645,1708106,1824627,1708366,1815176,1856267,1708370,1707637,1708367,1708373,1708375,1820850,1815650]&attributeId=904221228984762040&entryId=1707645&entryType=TAG&specIds=[269603]"
    page.get(url)
    
    packet = page.listen.wait(timeout=5)
    if packet:
        print("API was called!")
        print("Request body:", packet.request.postData)
    else:
        print("No API called")
    
    page.quit()
except Exception as e:
    print("ERROR:", e)
