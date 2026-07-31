let isSliding = false;

async function findSliderPixel(dataUrl) {
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    const bitmap = await createImageBitmap(blob);
    
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(bitmap, 0, 0);
    const imageData = ctx.getImageData(0, 0, bitmap.width, bitmap.height);
    const data = imageData.data;
    
    for (let y = 0; y < bitmap.height; y += 4) {
        for (let x = 0; x < bitmap.width; x += 4) {
            const i = (y * bitmap.width + x) * 4;
            const r = data[i];
            const g = data[i+1];
            const b = data[i+2];
            
            // Orange detection: R>230, G:90-150, B<60
            if (r > 230 && g > 90 && g < 150 && b < 60) {
                // Verify it is a solid block to avoid false positives (e.g. text or borders)
                const checkY = y + 15;
                if (checkY < bitmap.height) {
                    const i2 = (checkY * bitmap.width + x) * 4;
                    if (data[i2] > 230 && data[i2+1] > 90 && data[i2+1] < 150 && data[i2+2] < 60) {
                        return { x: x, y: y };
                    }
                }
            }
        }
    }
    return null;
}

async function doVisualSlide(tabId, coords) {
    const target = { tabId: tabId };
    return new Promise((resolve) => {
        chrome.debugger.attach(target, '1.3', () => {
            if (chrome.runtime.lastError) {
                console.error("Debugger error:", chrome.runtime.lastError.message);
                return resolve();
            }

            const x = coords.x + 10; // offset slightly into the center of the button
            const y = coords.y + 10;

            chrome.debugger.sendCommand(target, 'Input.dispatchMouseEvent', {
                type: 'mouseMoved', x: x, y: y
            }, () => {
                chrome.debugger.sendCommand(target, 'Input.dispatchMouseEvent', {
                    type: 'mousePressed', button: 'left', clickCount: 1, x: x, y: y
                }, () => {
                    const steps = 30;
                    const stepX = 380 / steps;
                    let currentX = x;
                    let i = 0;

                    function doMove() {
                        if (i < steps) {
                            currentX += stepX;
                            chrome.debugger.sendCommand(target, 'Input.dispatchMouseEvent', {
                                type: 'mouseMoved', button: 'left', x: currentX, y: y + (Math.random() * 2 - 1)
                            }, () => {
                                i++;
                                setTimeout(doMove, 20); // 20ms * 30 = 600ms drag
                            });
                        } else {
                            chrome.debugger.sendCommand(target, 'Input.dispatchMouseEvent', {
                                type: 'mouseReleased', button: 'left', clickCount: 1, x: currentX, y: y
                            }, () => {
                                chrome.debugger.detach(target);
                                resolve();
                            });
                        }
                    }
                    setTimeout(doMove, 100);
                });
            });
        });
    });
}

// Background loop to constantly monitor the screen (every 2 seconds)
setInterval(() => {
    if (isSliding) return;
    
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        if (!tabs || tabs.length === 0) return;
        const tab = tabs[0];
        if (!tab.url || (!tab.url.includes("dd373.com") && !tab.url.includes("aliyun"))) return;

        chrome.tabs.captureVisibleTab(tab.windowId, {format: 'jpeg', quality: 50}, async (dataUrl) => {
            if (chrome.runtime.lastError || !dataUrl) return;
            
            try {
                const coords = await findSliderPixel(dataUrl);
                if (coords) {
                    console.log("Auto Slider: Found orange slider at visual coordinates:", coords);
                    isSliding = true;
                    await doVisualSlide(tab.id, coords);
                    setTimeout(() => { isSliding = false; }, 3000); // 3 seconds cooldown before trying again
                }
            } catch (e) {
                console.error("Auto Slider Visual Error:", e);
            }
        });
    });
}, 2000);
