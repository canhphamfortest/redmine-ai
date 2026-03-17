// Chức năng Custom Search cho Custom Features Plugin

(function() {
  'use strict';

  window.CustomFeatures = window.CustomFeatures || {};
  var Search = {};
  var Utils = window.CustomFeatures.Utils;

  /**
   * Tạo form element cho custom search box
   * @param {string} projectIdentifier - Identifier của project hiện tại (nếu có)
   * @returns {HTMLFormElement} Form element đã được cấu hình
   */
  Search.createSearchForm = function(projectIdentifier) {
    var form = document.createElement('form');
    form.method = 'GET';
    form.action = '/custom_search';
    form.style.cssText = 'display: inline-block;';
    form.className = 'custom-search-quick-form';

    // Thêm utf8 hidden field (yêu cầu của Rails để xử lý UTF-8)
    var utf8Input = document.createElement('input');
    utf8Input.type = 'hidden';
    utf8Input.name = 'utf8';
    utf8Input.value = '✓';
    form.appendChild(utf8Input);

    // Thêm project_id nếu có (để filter kết quả theo project)
    if (projectIdentifier) {
      var hiddenInput = document.createElement('input');
      hiddenInput.type = 'hidden';
      hiddenInput.name = 'project_id';
      hiddenInput.value = projectIdentifier;
      form.appendChild(hiddenInput);
    }

    return form;
  };

  /**
   * Tạo label element với link đến trang search
   * @param {string} projectIdentifier - Identifier của project hiện tại (nếu có)
   * @returns {HTMLLabelElement} Label element đã được cấu hình
   */
  Search.createSearchLabel = function(projectIdentifier) {
    var label = document.createElement('label');
    label.setAttribute('for', 'custom_q');
    label.style.cssText = 'display: inline-block; margin-right: 5px;';

    // Tạo link đến trang search chính
    var link = document.createElement('a');
    var searchUrl = '/custom_search';
    if (projectIdentifier) {
      searchUrl += '?project_id=' + encodeURIComponent(projectIdentifier);
    }
    link.href = searchUrl;
    link.textContent = 'AI Search';
    label.appendChild(link);
    label.appendChild(document.createTextNode(': '));

    return label;
  };

  /**
   * Tạo input element cho search box
   * @returns {HTMLInputElement} Input element đã được cấu hình
   */
  Search.createSearchInput = function() {
    var input = document.createElement('input');
    input.type = 'text';
    input.name = 'q';
    input.id = 'custom_q';
    input.size = 20;
    input.className = 'small';
    input.placeholder = 'AI search...';
    input.style.cssText = 'display: inline-block;';

    return input;
  };

  /**
   * Chèn custom search box vào DOM sau quick-search element
   * @param {HTMLElement} quickSearch - Quick search element hiện tại
   * @param {HTMLElement} customSearchBox - Custom search box element cần chèn
   */
  Search.insertAfterQuickSearch = function(quickSearch, customSearchBox) {
    // Chèn sau quick-search, nếu có nextSibling thì chèn trước nó
    if (quickSearch.nextSibling) {
      quickSearch.parentNode.insertBefore(customSearchBox, quickSearch.nextSibling);
    } else {
      // Nếu không có nextSibling, append vào cuối parent
      quickSearch.parentNode.appendChild(customSearchBox);
    }
  };

  /**
   * Chèn custom search box bên cạnh quick-search
   * Hàm này sẽ tự động retry nếu quick-search chưa sẵn sàng
   */
  Search.insertCustomSearchBox = function() {
    var quickSearch = document.getElementById('quick-search');
    
    // Nếu quick-search chưa tồn tại, thử lại sau 100ms (cho trường hợp AJAX load)
    if (!quickSearch) {
      setTimeout(Search.insertCustomSearchBox, 100);
      return;
    }

    // Kiểm tra xem custom search box đã được thêm chưa (tránh duplicate)
    if (quickSearch.parentNode.querySelector('#custom-quick-search')) {
      return;
    }

    var projectIdentifier = Utils.getProjectIdentifierFromUrl();

    // Tạo container cho custom search box
    var customSearchBox = document.createElement('div');
    customSearchBox.id = 'custom-quick-search';
    customSearchBox.style.cssText = 'display: inline-block; margin-left: 15px; vertical-align: middle;';

    // Tạo và lắp ráp các components
    var form = Search.createSearchForm(projectIdentifier);
    var label = Search.createSearchLabel(projectIdentifier);
    var input = Search.createSearchInput();

    // Lắp ráp form
    form.appendChild(label);
    form.appendChild(input);
    customSearchBox.appendChild(form);

    // Chèn vào DOM
    Search.insertAfterQuickSearch(quickSearch, customSearchBox);
  };

  /**
   * Thiết lập jQuery handlers cho custom search form
   * @param {jQuery} $ - jQuery object
   */
  Search.setupJQueryHandlers = function($) {
    // Validate form submit - đảm bảo có query trước khi submit
    $('.custom-search-form, .custom-search-quick-form').on('submit', function(e) {
      var query = $(this).find('input[name="q"]').val().trim();
      if (!query) {
        e.preventDefault();
        Utils.notify('Vui lòng nhập từ khóa tìm kiếm', 'error');
        return false;
      }
    });

    // Tự động focus search input (chỉ trên trang search chính)
    if ($('.custom-search-input').length) {
      $('.custom-search-input').focus();
    }
  };

  /**
   * Khởi tạo chức năng tìm kiếm
   * Thiết lập custom search box và các event handlers
   */
  Search.init = function() {
    // Chỉ bật khi project nằm trong danh sách đã cấu hình
    if (!Utils.isProjectEnabled()) {
      return;
    }
    // Khởi tạo khi DOM sẵn sàng
    Utils.onReady(function() {
      Search.insertCustomSearchBox();
      // Thử lại sau khi page load (cho trường hợp AJAX load chậm)
      setTimeout(Search.insertCustomSearchBox, 500);
    });

    // Thiết lập jQuery handlers nếu jQuery có sẵn
    if (typeof jQuery !== 'undefined') {
      jQuery(document).ready(function($) {
        Search.setupJQueryHandlers($);
      });
    }
  };

  // Expose Search
  window.CustomFeatures.Search = Search;
})();

