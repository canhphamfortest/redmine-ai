// Chức năng tạo checklist cho Custom Features Plugin

(function() {
  'use strict';

  window.CustomFeatures = window.CustomFeatures || {};
  var Checklist = {};
  var Utils = window.CustomFeatures.Utils;

  /**
   * Di chuyển cursor đến cuối textarea
   * @param {HTMLTextAreaElement} textarea - Textarea element
   */
  Checklist.moveCursorToEnd = function(textarea) {
    try {
      if (textarea.setSelectionRange) {
        // Modern browsers
        var len = textarea.value.length;
        textarea.setSelectionRange(len, len);
      } else if (textarea.createTextRange) {
        // IE
        var range = textarea.createTextRange();
        range.collapse(false);
        range.select();
      }
    } catch (e) {
      // Bỏ qua nếu không thể set selection
    }
  };

  /**
   * Chèn checklist vào textarea
   * @param {HTMLTextAreaElement} textarea - Textarea element để chèn checklist
   * @param {string} checklistText - Nội dung checklist cần chèn
   * @returns {boolean} true nếu thành công, false nếu thất bại
   */
  Checklist.insertChecklistIntoTextarea = function(textarea, checklistText) {
    if (!textarea) return false;

    var currentContent = textarea.value || '';
    var newContent = currentContent.trim() 
      ? currentContent + '\n\n' + checklistText 
      : checklistText;

    textarea.value = newContent;

    // Kích hoạt events
    Utils.triggerEvent(textarea, 'input');
    Utils.triggerEvent(textarea, 'change');

    // jQuery trigger nếu có
    if (typeof jQuery !== 'undefined' && jQuery(textarea).length) {
      jQuery(textarea).trigger('input').trigger('change');
    }

    // Scroll và focus vào textarea
    setTimeout(function() {
      textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(function() {
        textarea.focus();
        Checklist.moveCursorToEnd(textarea);
      }, 200);
    }, 100);

    Utils.notify('Draft note với check list đã được tạo. Bạn có thể chỉnh sửa và submit.', 'success');
    return true;
  };

  /**
   * Tìm notes textarea trong form
   * Thử nhiều selector khác nhau để tương thích với các phiên bản Redmine
   * @returns {HTMLTextAreaElement|null} Textarea element hoặc null nếu không tìm thấy
   */
  Checklist.findNotesTextarea = function() {
    var selectors = [
      'textarea#issue_notes',
      'textarea[name="issue[notes]"]',
      'textarea[name="notes"]',
      'textarea#notes',
      'textarea.wiki-edit',
      'textarea.notes',
      'textarea[id*="notes"]',
      'textarea[name*="notes"]'
    ];

    for (var i = 0; i < selectors.length; i++) {
      var textarea = document.querySelector(selectors[i]);
      if (textarea) {
        return textarea;
      }
    }

    // Fallback: tìm textarea đầu tiên trong issue form
    var forms = document.querySelectorAll('form');
    for (var j = 0; j < forms.length; j++) {
      var form = forms[j];
      var formAction = form.action || form.getAttribute('action') || '';
      if (formAction && (formAction.indexOf('/issues/') !== -1 || formAction.indexOf('update') !== -1 || formAction.indexOf('/edit') !== -1)) {
        var textareas = form.querySelectorAll('textarea');
        if (textareas.length > 0) {
          return textareas[0];
        }
      }
    }

    return null;
  };

  /**
   * Hiển thị hoặc ẩn loading indicator cho button
   * @param {HTMLElement} button - Button element cần hiển thị loading
   * @param {boolean} show - true để hiển thị, false để ẩn
   */
  Checklist.showLoadingIndicator = function(button, show) {
    if (!button) return;

    var wrapper = button.parentNode;
    var loadingId = 'custom-checklist-loading-' + (button.id || 'default');
    var loadingIndicator = document.getElementById(loadingId);

    if (show) {
      if (!loadingIndicator) {
        loadingIndicator = document.createElement('span');
        loadingIndicator.id = loadingId;
        loadingIndicator.className = 'custom-checklist-loading';
        loadingIndicator.innerHTML = ' <span class="custom-loading-spinner"></span> <span class="custom-loading-text">AI Agent đang phân tích...</span>';
        loadingIndicator.style.cssText = 'margin-left: 10px; display: inline-block; vertical-align: middle; color: #666; font-size: 12px;';

        if (button.nextSibling) {
          wrapper.insertBefore(loadingIndicator, button.nextSibling);
        } else {
          wrapper.appendChild(loadingIndicator);
        }
      } else {
        loadingIndicator.style.display = 'inline-block';
      }

      // Disable button
      if (button.tagName === 'A') {
        button.style.pointerEvents = 'none';
        button.style.opacity = '0.6';
        button.style.cursor = 'not-allowed';
        button.setAttribute('data-loading', 'true');
      } else {
        button.disabled = true;
        button.style.opacity = '0.6';
        button.style.cursor = 'not-allowed';
      }
    } else {
      if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
      }

      // Kích hoạt button
      if (button.tagName === 'A') {
        button.style.pointerEvents = '';
        button.style.opacity = '1';
        button.style.cursor = 'pointer';
        button.removeAttribute('data-loading');
      } else {
        button.disabled = false;
        button.style.opacity = '1';
        button.style.cursor = 'pointer';
      }
    }
  };

  /**
   * Xử lý phản hồi thành công từ server
   * @param {Object} response - Response object từ server
   * @param {HTMLElement} button - Button element
   */
  Checklist.handleCreateDraftNoteSuccess = function(response, button) {
    Utils.notify(response.message || 'Draft note với checklist đã được tạo thành công!', 'success');
    setTimeout(function() {
      if (response.redirect_url) {
        window.location.href = response.redirect_url;
      } else {
        window.location.reload();
      }
    }, 1000);
  };

  /**
   * Xử lý lỗi từ server response
   * @param {number} status - HTTP status code
   * @param {Object} response - Response object (có thể null)
   */
  Checklist.handleCreateDraftNoteError = function(status, response) {
    if (status === 403) {
      Utils.notify('Bạn không có quyền chỉnh sửa issue này', 'error');
    } else if (status === 404) {
      Utils.notify('Không tìm thấy issue', 'error');
    } else if (response && response.message) {
      Utils.notify(response.message || 'Có lỗi xảy ra khi tạo note', 'error', 5000);
    } else {
      Utils.notify('Có lỗi xảy ra: ' + status, 'error');
    }
  };

  /**
   * Tạo draft note với checklist sử dụng AI Agent
   * @param {HTMLElement} clickedButton - Button được click (optional)
   * @returns {boolean} true nếu request được gửi thành công
   */
  Checklist.createDraftNoteWithChecklist = function(clickedButton) {
    var issueId = Utils.getIssueIdFromUrl();
    if (!issueId) {
      Utils.notify('Không tìm thấy issue ID. Vui lòng đảm bảo bạn đang ở trang issue detail.', 'error');
      return false;
    }

    // Tìm button element
    var button = clickedButton || 
                 document.getElementById('custom-create-draft-note-btn') || 
                 document.querySelector('.custom-create-draft-note');

    Checklist.showLoadingIndicator(button, true);

    // Tạo và cấu hình XMLHttpRequest
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/issues/' + issueId + '/create_draft_note', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    // Lấy và set CSRF token (bảo mật Rails)
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
      xhr.setRequestHeader('X-CSRF-Token', csrfToken.getAttribute('content'));
    }

    // Xử lý response thành công
    xhr.onload = function() {
      Checklist.showLoadingIndicator(button, false);

      if (xhr.status === 200) {
        try {
          var response = JSON.parse(xhr.responseText);
          if (response.success) {
            Checklist.handleCreateDraftNoteSuccess(response, button);
          } else {
            Checklist.handleCreateDraftNoteError(xhr.status, response);
          }
        } catch (e) {
          console.error('Error parsing response:', e);
          Utils.notify('Có lỗi xảy ra khi xử lý phản hồi từ server', 'error');
        }
      } else {
        Checklist.handleCreateDraftNoteError(xhr.status, null);
      }
    };

    // Xử lý lỗi kết nối
    xhr.onerror = function() {
      Checklist.showLoadingIndicator(button, false);
      Utils.notify('Không thể kết nối đến server', 'error');
    };

    // Xử lý timeout (AI Agent có thể mất nhiều thời gian)
    xhr.ontimeout = function() {
      Checklist.showLoadingIndicator(button, false);
      Utils.notify('Request timeout. AI Agent có thể đang xử lý, vui lòng thử lại sau.', 'error');
    };

    xhr.timeout = 360000; // 360 seconds (6 phút)
    xhr.send(JSON.stringify({}));
    return true;
  };

  /**
   * Kiểm tra và populate checklist từ sessionStorage
   * Sử dụng khi chuyển từ trang issue detail sang trang edit
   */
  Checklist.checkAndPopulateChecklistFromStorage = function() {
    var storedChecklist = sessionStorage.getItem('custom_draft_note_checklist');
    if (!storedChecklist) return;

    var attempts = 0;
    var maxAttempts = 10;

    function tryPopulate() {
      attempts++;
      var notesTextarea = Checklist.findNotesTextarea();

      if (notesTextarea) {
        Checklist.insertChecklistIntoTextarea(notesTextarea, storedChecklist);
        sessionStorage.removeItem('custom_draft_note_checklist');
      } else if (attempts < maxAttempts) {
        setTimeout(tryPopulate, 300);
      } else {
        sessionStorage.removeItem('custom_draft_note_checklist');
        console.warn('CustomFeatures: Không tìm thấy textarea notes để populate checklist');
      }
    }

    setTimeout(tryPopulate, 300);
  };

  /**
   * Tìm vị trí chèn button vào relations div
   * @param {HTMLElement} relationsDiv - Relations div element
   * @returns {HTMLElement|null} Element để chèn trước, hoặc null nếu append vào cuối
   */
  Checklist.findRelationsInsertPosition = function(relationsDiv) {
    // Ưu tiên chèn sau relations form
    var relationsForm = relationsDiv.querySelector('#new-relation-form');
    if (relationsForm) {
      return relationsForm.nextSibling;
    }

    // Nếu không có form, tìm paragraph "Related issues"
    var paragraphs = relationsDiv.querySelectorAll('p');
    for (var p = 0; p < paragraphs.length; p++) {
      var paraText = paragraphs[p].textContent || paragraphs[p].innerText || '';
      if (paraText.indexOf('Related issues') !== -1 || paraText.indexOf('Related') !== -1) {
        return paragraphs[p].nextSibling;
      }
    }

    return null;
  };

  /**
   * Clone button elements từ container
   * @param {HTMLElement} buttonContainer - Container chứa button gốc
   * @returns {Object|null} Object chứa cloned button và span, hoặc null nếu không tìm thấy
   */
  Checklist.cloneButtonElements = function(buttonContainer) {
    var button = buttonContainer.querySelector('#custom-create-draft-note-btn');
    var span = buttonContainer.querySelector('span');

    if (!button || !span) {
      return null;
    }

    return {
      button: button.cloneNode(true),
      span: span.cloneNode(true)
    };
  };

  /**
   * Chèn button vào relations div
   * @param {HTMLElement} relationsDiv - Relations div element
   * @param {HTMLElement} wrapperDiv - Wrapper div chứa button
   */
  Checklist.insertButtonIntoRelations = function(relationsDiv, wrapperDiv) {
    var insertPosition = Checklist.findRelationsInsertPosition(relationsDiv);

    if (insertPosition) {
      relationsDiv.insertBefore(wrapperDiv, insertPosition);
    } else {
      relationsDiv.appendChild(wrapperDiv);
    }
  };

  /**
   * Di chuyển draft note button đến phần relations
   * Button sẽ được hiển thị gần phần "Related issues" để dễ truy cập
   * @returns {boolean} true nếu thành công, false nếu thất bại
   */
  Checklist.moveDraftNoteButtonToRelations = function() {
    var relationsDiv = document.getElementById('relations');
    var buttonContainer = document.getElementById('custom-draft-note-button-container');

    if (!relationsDiv || !buttonContainer) {
      return false;
    }

    // Kiểm tra xem đã được di chuyển chưa (tránh duplicate)
    var existingInRelations = relationsDiv.querySelector('#custom-draft-note-button-wrapper');
    if (existingInRelations) {
      existingInRelations.style.display = '';
      return true;
    }

    // Nếu button container đã ở trong relations, chỉ cần update style
    if (buttonContainer.parentNode && buttonContainer.parentNode.id === 'relations') {
      buttonContainer.id = 'custom-draft-note-button-wrapper';
      buttonContainer.style.cssText = 'margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;';
      return true;
    }

    // Tạo wrapper div với styling
    var wrapperDiv = document.createElement('div');
    wrapperDiv.id = 'custom-draft-note-button-wrapper';
    wrapperDiv.style.cssText = 'margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;';

    // Clone button elements
    var clonedElements = Checklist.cloneButtonElements(buttonContainer);
    if (clonedElements) {
      wrapperDiv.appendChild(clonedElements.button);
      wrapperDiv.appendChild(clonedElements.span);

      // Chèn vào relations div
      Checklist.insertButtonIntoRelations(relationsDiv, wrapperDiv);
    }

    return true;
  };

  /**
   * Thiết lập MutationObserver để tự động di chuyển button khi DOM thay đổi
   * @param {HTMLElement} relationsDiv - Relations div element
   */
  Checklist.setupMutationObserver = function(relationsDiv) {
    if (typeof MutationObserver === 'undefined') {
      return;
    }

    var observer = new MutationObserver(function(mutations) {
      var shouldMove = false;
      mutations.forEach(function(mutation) {
        if (mutation.addedNodes.length > 0 || mutation.type === 'childList') {
          shouldMove = true;
        }
      });
      if (shouldMove) {
        setTimeout(function() {
          if (typeof Checklist.moveDraftNoteButtonToRelations === 'function') {
            Checklist.moveDraftNoteButtonToRelations();
          }
        }, 100);
      }
    });

    observer.observe(relationsDiv, {
      childList: true,
      subtree: true
    });
  };

  /**
   * Thiết lập jQuery event handlers
   * @param {jQuery} $ - jQuery object
   */
  Checklist.setupJQueryHandlers = function($) {
    // Handler cho button tạo note với checklist
    $(document).on('click', '.custom-create-draft-note, #custom-create-draft-note-btn', function(e) {
      e.preventDefault();
      var $button = $(this);

      // Kiểm tra button đã bị disable hoặc đang loading
      if ($button.prop('disabled') || $button.attr('data-loading') === 'true') {
        return false;
      }

      // Xác nhận trước khi tạo checklist
      if (confirm('Bạn có chắc muốn tạo một draft note mới với checklist được tạo bởi AI Agent?\n\nAI Agent sẽ phân tích nội dung issue và tạo checklist phù hợp.')) {
        Checklist.createDraftNoteWithChecklist(this);
      }
    });

    // Tự động di chuyển button khi AJAX hoàn thành (cho dynamic content)
    $(document).ajaxComplete(function() {
      setTimeout(function() {
        if (typeof Checklist.moveDraftNoteButtonToRelations === 'function') {
          Checklist.moveDraftNoteButtonToRelations();
        }
      }, 200);
    });

    // Thiết lập MutationObserver cho relations div
    var relationsDiv = document.getElementById('relations');
    if (relationsDiv) {
      Checklist.setupMutationObserver(relationsDiv);
    }
  };

  /**
   * Khởi tạo chức năng checklist
   * Thiết lập các event handlers và tự động di chuyển button vào relations section
   */
  Checklist.init = function() {

    // Chỉ bật khi project nằm trong danh sách đã cấu hình
    if (!Utils.isProjectEnabled()) {
      return;
    }

    // Expose functions ra global scope để có thể gọi từ HTML
    window.createDraftNoteWithChecklist = Checklist.createDraftNoteWithChecklist;
    window.moveDraftNoteButtonToRelations = Checklist.moveDraftNoteButtonToRelations;

    // Khởi tạo khi DOM sẵn sàng
    Utils.onReady(function() {
      Checklist.checkAndPopulateChecklistFromStorage();
      Checklist.moveDraftNoteButtonToRelations();

      // Retry sau các khoảng thời gian (cho trường hợp AJAX load chậm)
      setTimeout(Checklist.moveDraftNoteButtonToRelations, 300);
      setTimeout(Checklist.moveDraftNoteButtonToRelations, 800);
      setTimeout(Checklist.moveDraftNoteButtonToRelations, 1500);
    });

    // Retry populate checklist từ storage
    setTimeout(Checklist.checkAndPopulateChecklistFromStorage, 1000);

    // Thiết lập jQuery handlers nếu jQuery có sẵn
    if (typeof jQuery !== 'undefined') {
      jQuery(document).ready(function($) {
        Checklist.setupJQueryHandlers($);
      });
    }
  };

  // Expose Checklist
  window.CustomFeatures.Checklist = Checklist;
})();

