const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const os = require('os');

function generateHumanSteps(distance) {
    const steps = [];
    let currentX = 0;
    let currentY = 0;

    const overshoot = distance > 100 ? (4 + Math.random() * 4) : (2 + Math.random() * 3);
    const targetOvershootX = distance + overshoot;

    const mainStepsCount = Math.floor(22 + Math.random() * 8);
    for (let i = 1; i <= mainStepsCount; i++) {
        const t = i / mainStepsCount;
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        const nextX = targetOvershootX * ease;
        const dx = nextX - currentX;
        const dxJitter = (t > 0.1 && t < 0.9) ? dx + (Math.random() * 0.6 - 0.3) : dx;
        const dy = Math.sin(t * Math.PI) * (Math.random() * 0.8 + 0.2) + (Math.random() * 0.6 - 0.3);

        currentX += dxJitter;
        currentY += dy;
        steps.push({ dx: dxJitter, dy: dy });
    }

    const correctionStepsCount = Math.floor(5 + Math.random() * 4);
    const startCorrX = currentX;
    const deltaBack = distance - startCorrX;

    for (let j = 1; j <= correctionStepsCount; j++) {
        const t = j / correctionStepsCount;
        const ease = Math.sin(t * Math.PI / 2);
        const nextX = startCorrX + deltaBack * ease;
        const dx = nextX - currentX;
        const dy = Math.random() * 0.4 - 0.2;

        currentX = nextX;
        currentY += dy;
        steps.push({ dx: dx, dy: dy });
    }

    const totalDx = steps.reduce((sum, s) => sum + s.dx, 0);
    const diff = distance - totalDx;
    if (Math.abs(diff) > 0.0001 && steps.length > 0) {
        steps[steps.length - 1].dx += diff;
    }

    return steps;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function main() {
    const url = process.argv[2];
    if (!url) {
        console.log(JSON.stringify({ success: false, error: 'No URL provided' }));
        process.exit(1);
    }

    const profileDir = path.join(__dirname, '..', '..', 'data', 'dd373_puppeteer_profile');
    if (!fs.existsSync(profileDir)) {
        fs.mkdirSync(profileDir, { recursive: true });
    }

    let executablePath;
    const homedir = os.homedir();
    const possiblePaths = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/snap/bin/chromium',
        path.join(homedir, '.cache', 'ms-playwright', 'chromium-1112', 'chrome-linux', 'chrome'),
        path.join(homedir, '.cache', 'ms-playwright', 'chromium-1234', 'chrome-linux64', 'chrome')
    ];
    // Dynamic glob match for any ms-playwright chromium build
    try {
        const cacheDir = path.join(homedir, '.cache', 'ms-playwright');
        if (fs.existsSync(cacheDir)) {
            const dirs = fs.readdirSync(cacheDir);
            for (const d of dirs) {
                if (d.startsWith('chromium-')) {
                    const p1 = path.join(cacheDir, d, 'chrome-linux', 'chrome');
                    const p2 = path.join(cacheDir, d, 'chrome-linux64', 'chrome');
                    if (fs.existsSync(p1)) possiblePaths.push(p1);
                    if (fs.existsSync(p2)) possiblePaths.push(p2);
                }
            }
        }
    } catch (e) {}

    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            executablePath = p;
            break;
        }
    }

    let browser;
    try {
        const launchOptions = {
            headless: false,
            userDataDir: profileDir,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--silent-debugger-extension-api',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--lang=zh-CN,zh'
            ]
        };
        if (executablePath) {
            launchOptions.executablePath = executablePath;
        }

        browser = await puppeteer.launch(launchOptions);

        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36");

        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });

            // Visual Red Glowing Mouse Cursor Helper for Screen Recording & Debugging
            document.addEventListener('DOMContentLoaded', () => {
                const box = document.createElement('div');
                box.id = 'visual-mouse-pointer';
                box.style.position = 'fixed';
                box.style.top = '0px';
                box.style.left = '0px';
                box.style.width = '16px';
                box.style.height = '16px';
                box.style.backgroundColor = 'rgba(255, 0, 0, 0.95)';
                box.style.border = '2px solid #ffffff';
                box.style.borderRadius = '50%';
                box.style.pointerEvents = 'none';
                box.style.zIndex = '99999999';
                box.style.boxShadow = '0 0 12px rgba(255, 0, 0, 1.0)';
                box.style.transform = 'translate(-50%, -50%)';
                document.body.appendChild(box);

                window.addEventListener('mousemove', (e) => {
                    box.style.left = e.clientX + 'px';
                    box.style.top = e.clientY + 'px';
                });
            });
        });

        try {
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        } catch (e) {
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        }
        await sleep(2000);

        let content = await page.content();
        let solved = false;

        if (content.includes('aliyunCaptcha') || content.includes('sliding-slider') || content.includes('verify that you are a real person')) {
            const selectors = [
                '#aliyunCaptcha-sliding-slider',
                '.aliyunCaptcha-sliding-slider',
                '.aliyunCaptcha-sliding-btn',
                'div[class*="sliding-btn"]',
                '#nc_1_n1z',
                '.btn_slide'
            ];

            let sliderHandle = null;
            for (const sel of selectors) {
                sliderHandle = await page.$(sel);
                if (sliderHandle) break;
            }

            if (sliderHandle) {
                const box = await sliderHandle.boundingBox();
                if (box) {
                    let slideDistance = 320.0;
                    const trackSelectors = [
                        '#aliyunCaptcha-sliding-body',
                        '.sliding',
                        '#aliyunCaptcha-sliding-wrapper',
                        '.aliyunCaptcha-sliding-wrapper'
                    ];

                    for (const tSel of trackSelectors) {
                        const trackHandle = await page.$(tSel);
                        if (trackHandle) {
                            const tBox = await trackHandle.boundingBox();
                            if (tBox && tBox.width > box.width) {
                                const measured = tBox.width - box.width;
                                if (measured > 250 && measured < 380) {
                                    slideDistance = measured;
                                }
                                break;
                            }
                        }
                    }

                    const startX = box.x + box.width / 2;
                    const startY = box.y + box.height / 2;

                    await page.mouse.move(startX, startY);
                    await sleep(150);
                    await page.mouse.down();
                    await sleep(250);

                    let currX = startX;
                    let currY = startY;
                    const steps = generateHumanSteps(slideDistance);

                    for (const step of steps) {
                        currX += step.dx;
                        currY += step.dy;
                        await page.mouse.move(currX, currY);
                        await sleep(15 + Math.random() * 15);
                    }

                    await sleep(400);
                    await page.mouse.up();
                    await sleep(2500);

                    content = await page.content();
                }
            }
        } else {
            solved = true;
        }

        // Additional sleep & DOM verification for AJAX price table
        if (!content.includes('aliyunCaptcha')) {
            if (content.includes('元/个') || content.includes('1元=') || content.includes('1元 =')) {
                solved = true;
            } else {
                await sleep(2000);
                content = await page.content();
                if (content.includes('元/个') || content.includes('1元=') || content.includes('1元 =')) {
                    solved = true;
                }
            }
        }

        const logDir = path.join(__dirname, '..', '..', 'data', 'logs');
        if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
        const screenshotPath = path.join(logDir, 'dd373_last_error.png');

        if (!solved) {
            await page.screenshot({ path: screenshotPath, fullPage: true });
        }

        const cookies = await page.cookies();
        const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

        console.log(JSON.stringify({
            success: true,
            solved: solved,
            cookies: cookieStr,
            html: content,
            has_screenshot: !solved
        }));

    } catch (err) {
        console.log(JSON.stringify({ success: false, error: err.message }));
    } finally {
        if (browser) await browser.close();
    }
}

main();
