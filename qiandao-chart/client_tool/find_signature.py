import requests
import re
import os

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    html = requests.get('https://qiandao.com/', headers=headers).text
    # Tìm tất cả các file JS
    js_urls = []
    
    # Next.js thường để JS trong _next/static/
    for match in re.findall(r'src="([^"]+\.js.*?)"', html):
        url = match if match.startswith('http') else 'https://qiandao.com' + match
        js_urls.append(url)
        
    print(f"Found {len(js_urls)} JS files.")
    
    found = False
    for j_url in js_urls:
        try:
            print(f"Checking {j_url}")
            js_content = requests.get(j_url, headers=headers).text
            if 'x-request-sign' in js_content or 'HMAC_SHA256' in js_content:
                print(f"\n[+] FOUND SIGNATURE LOGIC IN: {j_url}")
                # Print around the match
                idx = js_content.find('x-request-sign')
                if idx == -1: idx = js_content.find('HMAC_SHA256')
                start = max(0, idx - 200)
                end = min(len(js_content), idx + 200)
                print("Snippet:", js_content[start:end])
                found = True
                break
        except Exception as e:
            print(f"Failed to fetch {j_url}: {e}")
            
    if not found:
        print("Could not find signature logic in the main HTML JS files.")
        
except Exception as e:
    print("ERROR:", e)
