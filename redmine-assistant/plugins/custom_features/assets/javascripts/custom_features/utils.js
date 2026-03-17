// Các hàm tiện ích cho Custom Features Plugin
// Module này cung cấp các utility functions được sử dụng bởi các modules khác

(function() {
  'use strict';

  window.CustomFeatures = window.CustomFeatures || {};
  var Utils = {};

  /**
   * Escape HTML để ngăn chặn XSS (Cross-Site Scripting) attacks
   * Chuyển đổi các ký tự đặc biệt HTML thành HTML entities
   * 
   * @param {string} text - Text cần escape
   * @returns {string} Text đã được escape, hoặc '' nếu text rỗng/null
   */
  Utils.escapeHtml = function(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  };

  /**
   * Kích hoạt event trên element (tương thích cross-browser)
   * Hỗ trợ cả modern browsers và IE cũ
   * 
   * @param {HTMLElement} element - Element cần trigger event
   * @param {string} eventName - Tên event (ví dụ: 'click', 'change')
   * @param {boolean} bubbles - Event có bubble không (mặc định: true)
   */
  Utils.triggerEvent = function(element, eventName, bubbles) {
    bubbles = bubbles !== false;
    try {
      var event = document.createEvent('HTMLEvents');
      event.initEvent(eventName, bubbles, true);
      element.dispatchEvent(event);
    } catch (e) {
      try {
        var event = new Event(eventName, { bubbles: bubbles });
        element.dispatchEvent(event);
      } catch (e2) {
        // Fallback cho các trình duyệt cũ
        if (typeof jQuery !== 'undefined' && jQuery(element).length) {
          jQuery(element).trigger(eventName);
        }
      }
    }
  };

  /**
   * Lấy issue ID từ URL hiện tại
   * Parse URL để tìm pattern /issues/:id
   * 
   * @returns {string|null} Issue ID hoặc null nếu không tìm thấy
   */
  Utils.getIssueIdFromUrl = function() {
    var match = window.location.pathname.match(/\/issues\/(\d+)/);
    return match ? match[1] : null;
  };

  /**
   * Lấy project identifier từ URL hiện tại
   * Parse URL để tìm pattern /projects/:identifier
   * 
   * @returns {string} Project identifier hoặc '' nếu không tìm thấy
   */
  Utils.getProjectIdentifierFromUrl = function() {
    var match = window.location.pathname.match(/\/projects\/([^\/]+)/);
    return match && match[1] ? match[1] : '';
  };

  /**
   * Lấy project identifier từ nhiều nguồn khác nhau (URL, script rm.AutoComplete, DOM)
   *
   * @returns {string} Project identifier hoặc '' nếu không tìm thấy
   */
  Utils.getCurrentProjectIdentifier = function() {
    var identifier = Utils.getProjectIdentifierFromUrl();
    if (identifier) {
      return identifier;
    }

    // Thử lấy từ rm.AutoComplete (được Redmine inject vào trang issue)
    try {
      if (window.rm && rm.AutoComplete && rm.AutoComplete.dataSources) {
        var sources = rm.AutoComplete.dataSources;
        var url = sources.issues || sources.wiki_pages || '';
        var match = url.match(/project_id=([^&]+)/);
        if (match && match[1]) {
          return decodeURIComponent(match[1]);
        }
      }
    } catch (e) {
      // Bỏ qua nếu không parse được
    }

    // Thử tìm link tới project trong breadcrumb/header
    // Bỏ qua các link có jump=projects (thường là filter/navigation links)
    var projectLinks = document.querySelectorAll('a[href^="/projects/"]');
    for (var i = 0; i < projectLinks.length; i++) {
      var projectLink = projectLinks[i];
      var href = projectLink.getAttribute('href');
      
      // Bỏ qua link có jump=projects (filter/navigation)
      if (href.indexOf('jump=projects') !== -1) {
        continue;
      }
      
      var projectHrefMatch = href.match(/\/projects\/([^\/?#]+)/);
      if (projectHrefMatch && projectHrefMatch[1]) {
        identifier = projectHrefMatch[1];
        return identifier;
      }
    }

    return '';
  };

  /**
   * Kiểm tra project hiện tại có được bật tính năng hay không
   *
   * @param {string} projectIdentifier - Identifier của project (optional)
   * @returns {boolean} true nếu được bật, ngược lại false
   */
  Utils.isProjectEnabled = function(projectIdentifier) {
    var enabledProjects = window.CustomFeaturesEnabledProjects || [];
    if (!Array.isArray(enabledProjects)) {
      enabledProjects = [];
    }

    var identifier = projectIdentifier || Utils.getCurrentProjectIdentifier();
    if (!identifier) {
      return false;
    }

    return enabledProjects.indexOf(identifier) !== -1;
  };

  /**
   * Hiển thị thông báo cho người dùng
   * Sử dụng jQuery.notify nếu có, fallback về alert nếu không
   * 
   * @param {string} message - Nội dung thông báo
   * @param {string} type - Loại thông báo: 'info', 'success', 'error', 'warning' (mặc định: 'info')
   * @param {number} delay - Thời gian hiển thị (milliseconds, mặc định: 3000)
   */
  Utils.notify = function(message, type, delay) {
    type = type || 'info';
    delay = delay || 3000;

    if (typeof jQuery !== 'undefined' && jQuery.notify) {
      jQuery.notify(message, {
        type: type,
        delay: delay
      });
    } else {
      alert(message);
    }
  };

  /**
   * Đợi DOM element xuất hiện (polling)
   * Hữu ích khi element được load bởi AJAX hoặc dynamic content
   * 
   * @param {string} selector - CSS selector của element cần đợi
   * @param {Function} callback - Callback function được gọi khi element xuất hiện
   * @param {number} maxAttempts - Số lần thử tối đa (mặc định: 20)
   */
  Utils.waitForElement = function(selector, callback, maxAttempts) {
    maxAttempts = maxAttempts || 20;
    var attempts = 0;

    function check() {
      attempts++;
      var element = document.querySelector(selector);
      if (element) {
        callback(element);
      } else if (attempts < maxAttempts) {
        setTimeout(check, 100);
      }
    }

    check();
  };

  /**
   * Kiểm tra xem DOM đã sẵn sàng chưa và thực thi callback
   * Tương tự như jQuery.ready() nhưng không phụ thuộc jQuery
   * 
   * @param {Function} callback - Callback function được gọi khi DOM sẵn sàng
   */
  Utils.onReady = function(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  };

  // Expose Utils
  window.CustomFeatures.Utils = Utils;
})();

