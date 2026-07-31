// Hàm tính toạ độ tuyệt đối (hỗ trợ cả iframe nếu cùng origin)
function getAbsoluteCoords(btn) {
  const rect = btn.getBoundingClientRect();
  let x = rect.left + rect.width / 2;
  let y = rect.top + rect.height / 2;
  try {
      let currentWindow = window;
      while (currentWindow !== window.top) {
          const frames = currentWindow.parent.document.querySelectorAll('iframe');
          for (let i = 0; i < frames.length; i++) {
              if (frames[i].contentWindow === currentWindow) {
                  const frRect = frames[i].getBoundingClientRect();
                  x += frRect.left;
                  y += frRect.top;
                  break;
              }
          }
          currentWindow = currentWindow.parent;
      }
  } catch (e) {
      // CORS block
  }
  return { x, y };
}

function trySlide() {
  // Tìm nút trượt và thanh nền của Aliyun WAF (hỗ trợ cả bản cũ nc_1_n1z và bản mới aliyunCaptcha)
  const btn = document.querySelector('#nc_1_n1z') || document.querySelector('.btn_slide') || document.querySelector('.sm-slider-btn') || document.querySelector('#aliyunCaptcha-sliding-slider') || document.querySelector('.aliyunCaptcha-sliding-slider');
  const wrapper = document.querySelector('#nc_1_wrapper') || document.querySelector('.nc-container') || document.querySelector('.sm-slider-track') || document.querySelector('#aliyunCaptcha-sliding-wrapper') || document.querySelector('#aliyunCaptcha-window-embed');

  // Nếu tìm thấy và chưa từng kéo
  if (btn && wrapper && !btn.hasAttribute('data-slided')) {
    const btnRect = btn.getBoundingClientRect();
    const wrapperRect = wrapper.getBoundingClientRect();

    if (btnRect.width > 0 && wrapperRect.width > 0) {
      btn.setAttribute('data-slided', 'true');
      console.log('Auto Slider: Bắt đầu tự động kéo...');

      const coords = getAbsoluteCoords(btn);

      // Gửi yêu cầu qua Background script để nó gọi Chrome Debugger API kéo thật 100%
      chrome.runtime.sendMessage({
        action: 'slide',
        x: coords.x,
        y: coords.y,
        width: 380
      }, (response) => {
          if (response && response.success) {
              console.log('Auto Slider: Kéo hoàn tất qua Debugger!');
          } else {
              console.log('Auto Slider: Debugger kéo thất bại!');
          }
      });
    }
  }
}

// Bắt sự kiện DOM thay đổi để trượt ngay khi thanh trượt hiện ra (cả trong popup/iframe)
const observer = new MutationObserver(() => {
  trySlide();
});
observer.observe(document.body, { childList: true, subtree: true });

// Check định kỳ (dành cho trường hợp WAF bị bắt reset lại)
setInterval(() => {
  const btn = document.querySelector('#nc_1_n1z') || document.querySelector('#aliyunCaptcha-sliding-slider');
  // Nếu bị lỗi (chữ đỏ báo kéo lại), gỡ cờ để kéo lại
  if (btn && (btn.classList.contains('errloading') || document.querySelector('.aliyunCaptcha-sliding-errorCode'))) {
    const refreshBtn = document.querySelector('a[href*="reset"]') || document.querySelector('.aliyunCaptcha-sliding-refresh');
    if (refreshBtn) refreshBtn.click();
    btn.removeAttribute('data-slided');
  }
  
  // Xóa cờ nếu slider reset về 0 (ví dụ web tự reload slider)
  if (btn && (btn.style.left === '0px' || btn.style.left === '')) {
     // btn.removeAttribute('data-slided');
  }

  trySlide();
}, 2000);
