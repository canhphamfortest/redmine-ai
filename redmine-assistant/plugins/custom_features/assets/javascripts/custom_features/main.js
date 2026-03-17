// Điểm vào chính cho Custom Features Plugin
// File này khởi tạo tất cả các modules

(function() {
  'use strict';

  // Đợi tất cả dependencies được load
  function init() {
    // Khởi tạo Utils trước (cần thiết cho các modules khác)
    if (typeof window.CustomFeatures === 'undefined' || !window.CustomFeatures.Utils) {
      setTimeout(init, 50);
      return;
    }

    // Khởi tạo tất cả các modules
    if (window.CustomFeatures.Search && typeof window.CustomFeatures.Search.init === 'function') {
      window.CustomFeatures.Search.init();
    }

    if (window.CustomFeatures.Checklist && typeof window.CustomFeatures.Checklist.init === 'function') {
      window.CustomFeatures.Checklist.init();
    }

    if (window.CustomFeatures.AutoLink && typeof window.CustomFeatures.AutoLink.init === 'function') {
      window.CustomFeatures.AutoLink.init();
    }
  }

  // Bắt đầu khởi tạo khi DOM sẵn sàng
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Cũng thử lại sau một khoảng thời gian để xử lý async loading
  setTimeout(init, 100);
})();

