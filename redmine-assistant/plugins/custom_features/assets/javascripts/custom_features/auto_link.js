// Chức năng Auto Link Related Issues cho Custom Features Plugin

(function() {
  'use strict';

  window.CustomFeatures = window.CustomFeatures || {};
  var AutoLink = {};
  var Utils = window.CustomFeatures.Utils;

  /**
   * Chèn auto link button bên cạnh button "Add" trong relations section
   */
  AutoLink.insertAutoLinkButton = function() {
    var relationsDiv = document.getElementById('relations');
    if (!relationsDiv) {
      setTimeout(AutoLink.insertAutoLinkButton, 100);
      return;
    }

    var contextualDiv = relationsDiv.querySelector('.contextual');
    if (!contextualDiv) {
      return;
    }

    // Kiểm tra xem đã được thêm chưa
    if (contextualDiv.querySelector('#custom-auto-link-btn')) {
      return;
    }

    // Tạo separator
    var separator = document.createTextNode(' | ');

    // Tạo button
    var linkButton = document.createElement('a');
    linkButton.href = '#';
    linkButton.id = 'custom-auto-link-btn';
    linkButton.textContent = 'Auto Link Related Issues';
    linkButton.onclick = function(e) {
      e.preventDefault();
      AutoLink.autoLinkRelatedIssues();
      return false;
    };

    // Thêm vào contextual div
    contextualDiv.appendChild(separator);
    contextualDiv.appendChild(linkButton);
  };

  /**
   * Hàm chính để tự động liên kết issues liên quan
   * Sử dụng AI Agent để tìm và liên kết các issues có liên quan
   */
  AutoLink.autoLinkRelatedIssues = function() {
    var currentIssueId = Utils.getIssueIdFromUrl();
    if (!currentIssueId) {
      Utils.notify('Không thể xác định issue hiện tại', 'error');
      return;
    }

    // Lấy thông tin issue hiện tại
    AutoLink.getCurrentIssueInfo(currentIssueId, function(currentIssue) {
      if (!currentIssue) {
        currentIssue = { id: currentIssueId, subject: 'Issue #' + currentIssueId };
      }

      // Hiển thị dialog với trạng thái loading
      var overlay = AutoLink.showAutoLinkPreviewWithLoading(currentIssue);

      // Gọi AI Agent endpoint
      AutoLink.findRelatedIssuesWithAI(currentIssueId, function(response) {
        if (!response || !response.success) {
          var errorMsg = response && response.message ? response.message : 'Không thể tìm kiếm với AI Agent';
          AutoLink.updateAutoLinkPreview(overlay, currentIssue, [], errorMsg);
          return;
        }

        var relatedIssues = response.related_issues || [];

        if (relatedIssues.length === 0) {
          AutoLink.updateAutoLinkPreview(overlay, currentIssue, [], 'AI Agent không tìm thấy issues liên quan');
          return;
        }

        // Cập nhật dialog với kết quả
        AutoLink.updateAutoLinkPreview(overlay, currentIssue, relatedIssues);
      });
    });
  };

  /**
   * Lấy thông tin issue hiện tại từ proxy endpoint
   * Sử dụng session authentication của user đã đăng nhập
   * @param {string} issueId - ID của issue
   * @param {Function} callback - Callback function với issue data
   */
  AutoLink.getCurrentIssueInfo = function(issueId, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/issues/' + issueId + '/get_issue_info', true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.onload = function() {
      if (xhr.status === 200) {
        try {
          var response = JSON.parse(xhr.responseText);
          callback(response.issue);
        } catch (e) {
          console.error('Error parsing issue:', e);
          callback(null);
        }
      } else {
        console.error('Error fetching issue info. Status:', xhr.status);
        callback(null);
      }
    };

    xhr.onerror = function() {
      console.error('Network error when fetching issue info');
      callback(null);
    };

    xhr.send();
  };

  /**
   * Tìm issues liên quan sử dụng AI Agent
   * @param {string} issueId - ID của issue hiện tại
   * @param {Function} callback - Callback function với response từ AI
   */
  AutoLink.findRelatedIssuesWithAI = function(issueId, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/issues/' + issueId + '/find_related_issues', true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Accept', 'application/json');

    // Lấy CSRF token
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
      xhr.setRequestHeader('X-CSRF-Token', csrfToken.getAttribute('content'));
    }

    xhr.onload = function() {
      if (xhr.status === 200) {
        try {
          var response = JSON.parse(xhr.responseText);
          callback(response);
        } catch (e) {
          console.error('Error parsing AI response:', e);
          callback({ success: false, message: 'Lỗi khi parse phản hồi từ AI Agent' });
        }
      } else {
        try {
          var errorResponse = JSON.parse(xhr.responseText);
          callback({ success: false, message: errorResponse.message || 'Lỗi từ server' });
        } catch (e) {
          callback({ success: false, message: 'Lỗi khi gọi AI Agent (status: ' + xhr.status + ')' });
        }
      }
    };

    xhr.onerror = function() {
      callback({ success: false, message: 'Không thể kết nối đến server' });
    };

    xhr.ontimeout = function() {
      callback({ success: false, message: 'Timeout khi gọi AI Agent' });
    };

    xhr.timeout = 360000; // 360 seconds
    xhr.send();
  };

  /**
   * Hiển thị dialog với trạng thái loading
   * @param {Object} currentIssue - Thông tin issue hiện tại
   * @returns {HTMLElement} Overlay element
   */
  AutoLink.showAutoLinkPreviewWithLoading = function(currentIssue) {
    var overlay = document.createElement('div');
    overlay.id = 'custom-auto-link-overlay';
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 9998; display: flex; align-items: center; justify-content: center;';

    var dialog = document.createElement('div');
    dialog.id = 'custom-auto-link-dialog';
    dialog.style.cssText = 'background: white; padding: 20px; border-radius: 5px; max-width: 700px; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); z-index: 9999;';

    dialog.innerHTML = '<h3 style="margin-top: 0; color: #169;">🤖 AI-Detected Related Issues</h3>' +
      '<p style="color: #666; font-size: 13px; margin-bottom: 15px;">' +
      'AI Agent đang phân tích nội dung issue và tìm các issues liên quan đến ' +
      '<strong>#' + currentIssue.id + ': ' + Utils.escapeHtml(currentIssue.subject || 'Issue #' + currentIssue.id) + '</strong>' +
      '</p>' +
      '<div id="custom-auto-link-issues-container" style="max-height: 400px; overflow-y: auto; margin-bottom: 15px; min-height: 100px; display: flex; align-items: center; justify-content: center;">' +
      '<div style="text-align: center; color: #666;">' +
      '<div style="font-size: 16px; margin-bottom: 10px;">⏳ Đang tải...</div>' +
      '<div style="font-size: 13px;">AI Agent đang phân tích và tìm kiếm...</div>' +
      '</div>' +
      '</div>' +
      '<div style="text-align: right; margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">' +
      '<button id="custom-auto-link-cancel-btn" style="padding: 10px 20px 25px 20px; background: #f5f5f5; border: 1px solid #ccc; border-radius: 3px; cursor: pointer; font-size: 14px;">Cancel</button>' +
      '<button id="custom-auto-link-confirm-btn" style="padding: 10px 20px 25px 20px; background: #ccc; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 14px; font-weight: bold; cursor: not-allowed;" disabled>Đang tải...</button>' +
      '</div>';

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Event handlers
    document.getElementById('custom-auto-link-cancel-btn').onclick = function() {
      document.body.removeChild(overlay);
    };

    overlay.onclick = function(e) {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    };

    return overlay;
  };

  /**
   * Tính toán màu sắc dựa trên similarity percentage
   * @param {number} percent - Similarity percentage (0-100)
   * @returns {Object} Object chứa color và background color
   */
  AutoLink.calculateSimilarityColor = function(percent) {
    if (percent >= 80) {
      return { color: '#28a745', bg: '#d4edda' };
    } else if (percent >= 60) {
      return { color: '#5cb85c', bg: '#e8f5e9' };
    } else if (percent >= 40) {
      return { color: '#ffc107', bg: '#fff3cd' };
    } else {
      return { color: '#ff9800', bg: '#ffe0b2' };
    }
  };

  /**
   * Render HTML cho một issue trong danh sách
   * @param {Object} issue - Issue object
   * @param {number} index - Index của issue trong danh sách
   * @returns {string} HTML string
   */
  AutoLink.renderIssueItem = function(issue, index) {
    var statusClass = issue.status ? issue.status.name.toLowerCase().replace(/\s+/g, '-') : '';
    var priorityClass = issue.priority ? issue.priority.name.toLowerCase().replace(/\s+/g, '-') : '';

    // Tính similarity percentage
    var similarityPercent = issue.similarity_percentage !== undefined && issue.similarity_percentage !== null
      ? issue.similarity_percentage.toFixed(1)
      : (issue.similarity_score !== undefined && issue.similarity_score !== null
        ? (issue.similarity_score * 100).toFixed(1)
        : 'N/A');

    // Tính màu sắc dựa trên similarity
    var similarityColor = 'inherit';
    var similarityBg = 'transparent';
    if (similarityPercent !== 'N/A') {
      var percent = parseFloat(similarityPercent);
      var colors = AutoLink.calculateSimilarityColor(percent);
      similarityColor = colors.color;
      similarityBg = colors.bg;
    }

    // URL đến issue
    var issueUrl = '/issues/' + issue.id;

    var html = '<div class="auto-link-issue-card" data-issue-url="' + issueUrl + '" style="padding: 12px; border: 1px solid #ddd; border-radius: 3px; margin-bottom: 10px; background: #f9f9f9; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background=\'#f0f0f0\'" onmouseout="this.style.background=\'#f9f9f9\'">';
    
    // Checkbox ở góc trên bên trái (riêng biệt, không trong card clickable)
    html += '<div style="display: flex; align-items: flex-start;">';
    html += '<input type="checkbox" class="auto-link-issue-checkbox" data-issue-id="' + issue.id + '" checked style="margin-top: 3px; margin-right: 10px; cursor: pointer;" onclick="event.stopPropagation();">';
    
    // Nội dung issue (clickable để mở link)
    html += '<div class="auto-link-issue-content" style="flex: 1;">';
    
    html += '<div style="font-weight: bold; margin-bottom: 5px;">';
    html += '<span style="color: #169;">#' + issue.id + ' 🔗</span>';
    
    if (issue.status) {
      html += '<span class="issue-status ' + statusClass + '" style="margin-left: 5px; font-size: 11px; padding: 2px 6px; background: #e8f4f8; border-radius: 3px;">' + issue.status.name + '</span>';
    }
    
    if (issue.priority) {
      html += '<span class="issue-priority ' + priorityClass + '" style="margin-left: 5px; font-size: 11px; padding: 2px 6px; background: #fff3cd; border-radius: 3px;">' + issue.priority.name + '</span>';
    }
    
    html += '<span style="float: right; font-size: 12px; font-weight: bold; padding: 3px 8px; border-radius: 3px; background: ' + similarityBg + '; color: ' + similarityColor + ';">';
    html += '🤖 ' + similarityPercent + '% liên quan';
    html += '</span>';
    html += '</div>';
    
    html += '<div style="font-size: 13px; color: #333; margin-bottom: 5px;" class="auto-link-issue-title">' + Utils.escapeHtml(issue.subject || 'No subject') + '</div>';
    
    if (issue.assigned_to) {
      html += '<div style="font-size: 11px; color: #666;">👤 ' + Utils.escapeHtml(issue.assigned_to.name) + '</div>';
    }
    
    if (issue.tracker) {
      html += '<div style="font-size: 11px; color: #666;">📋 ' + Utils.escapeHtml(issue.tracker.name) + '</div>';
    }
    
    if (issue.project) {
      html += '<div style="font-size: 11px; color: #666;">📁 ' + Utils.escapeHtml(issue.project.name) + '</div>';
    }
    
    html += '</div>'; // Close content div
    html += '</div>'; // Close flex container
    
    html += '</div>'; // Close card
    return html;
  };

  /**
   * Render danh sách issues
   * @param {Array} relatedIssues - Mảng các issues liên quan
   * @returns {string} HTML string
   */
  AutoLink.renderIssuesList = function(relatedIssues) {
    var html = '<div style="margin-bottom: 15px;">';
    html += '<h4 style="margin: 10px 0; color: #333; display: inline-block;">Issues được tìm thấy:</h4>';
    html += '<div style="float: right;">';
    html += '<button id="auto-link-select-all" style="padding: 5px 10px; margin-right: 5px; background: #5cb85c; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">✓ Chọn tất cả</button>';
    html += '<button id="auto-link-deselect-all" style="padding: 5px 10px; background: #d9534f; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">✗ Bỏ chọn tất cả</button>';
    html += '</div>';
    html += '<div style="clear: both;"></div>';
    html += '</div>';
    
    relatedIssues.forEach(function(issue, index) {
      html += AutoLink.renderIssueItem(issue, index);
    });
    return html;
  };

  /**
   * Hiển thị trạng thái lỗi trong dialog
   * @param {HTMLElement} issuesContainer - Container element
   * @param {HTMLElement} confirmBtn - Confirm button element
   * @param {string} errorMsg - Thông báo lỗi
   */
  AutoLink.renderErrorState = function(issuesContainer, confirmBtn, errorMsg) {
    issuesContainer.innerHTML = '<div style="text-align: center; color: #d32f2f; padding: 20px;">' +
      '<div style="font-size: 16px; margin-bottom: 10px;">❌ Lỗi</div>' +
      '<div style="font-size: 13px;">' + Utils.escapeHtml(errorMsg) + '</div>' +
      '</div>';
    confirmBtn.style.display = 'none';
  };

  /**
   * Hiển thị trạng thái rỗng (không tìm thấy issues)
   * @param {HTMLElement} issuesContainer - Container element
   * @param {HTMLElement} confirmBtn - Confirm button element
   */
  AutoLink.renderEmptyState = function(issuesContainer, confirmBtn) {
    issuesContainer.innerHTML = '<div style="text-align: center; color: #ff9800; padding: 20px;">' +
      '<div style="font-size: 16px; margin-bottom: 10px;">⚠️ Không tìm thấy</div>' +
      '<div style="font-size: 13px;">AI Agent không tìm thấy issues liên quan</div>' +
      '</div>';
    confirmBtn.style.display = 'none';
  };

  /**
   * Cập nhật số lượng issues được chọn trong confirm button
   * @param {HTMLElement} confirmBtn - Confirm button element
   */
  AutoLink.updateSelectedCount = function(confirmBtn) {
    var checkboxes = document.querySelectorAll('.auto-link-issue-checkbox:checked');
    var count = checkboxes.length;
    
    if (count > 0) {
      confirmBtn.disabled = false;
      confirmBtn.style.background = '#5cb85c';
      confirmBtn.style.cursor = 'pointer';
      confirmBtn.textContent = '✓ Link ' + count + ' Issue(s)';
    } else {
      confirmBtn.disabled = true;
      confirmBtn.style.background = '#ccc';
      confirmBtn.style.cursor = 'not-allowed';
      confirmBtn.textContent = 'Chọn ít nhất 1 issue';
    }
  };

  /**
   * Cập nhật buttons và thông tin trong dialog
   * @param {HTMLElement} dialog - Dialog element
   * @param {HTMLElement} confirmBtn - Confirm button element
   * @param {Object} currentIssue - Issue hiện tại
   * @param {Array} relatedIssues - Mảng issues liên quan
   * @param {HTMLElement} overlay - Overlay element
   */
  AutoLink.updateDialogButtons = function(dialog, confirmBtn, currentIssue, relatedIssues, overlay) {
    // Cập nhật confirm button với số lượng ban đầu (tất cả được chọn)
    AutoLink.updateSelectedCount(confirmBtn);

    // Cập nhật title
    var title = dialog.querySelector('h3');
    if (title) {
      title.textContent = '🤖 AI-Detected Related Issues';
    }

    // Cập nhật description
    var desc = dialog.querySelector('p');
    if (desc) {
      desc.innerHTML = 'AI Agent đã phân tích nội dung issue và tìm thấy <strong>' + relatedIssues.length + '</strong> issue(s) liên quan đến ' +
        '<strong>#' + currentIssue.id + ': ' + Utils.escapeHtml(currentIssue.subject || 'Issue #' + currentIssue.id) + '</strong>';
    }

    // Thêm event handlers cho checkboxes
    var checkboxes = dialog.querySelectorAll('.auto-link-issue-checkbox');
    checkboxes.forEach(function(checkbox) {
      checkbox.addEventListener('change', function() {
        AutoLink.updateSelectedCount(confirmBtn);
      });
    });

    // Thêm event handlers cho issue cards (click để toggle checkbox)
    var issueCards = dialog.querySelectorAll('.auto-link-issue-card');
    issueCards.forEach(function(card) {
      card.addEventListener('click', function(e) {
        // Không toggle checkbox nếu click vào checkbox hoặc title
        if (e.target.classList.contains('auto-link-issue-checkbox') || 
            e.target.classList.contains('auto-link-issue-title')) {
          return;
        }
        
        // Toggle checkbox
        var checkbox = card.querySelector('.auto-link-issue-checkbox');
        if (checkbox) {
          checkbox.checked = !checkbox.checked;
          // Trigger change event để cập nhật số lượng
          var changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      });
    });

    // Thêm event handlers cho issue title (click để mở link)
    var issueTitles = dialog.querySelectorAll('.auto-link-issue-title');
    issueTitles.forEach(function(title) {
      // Thêm hover effect
      title.style.cursor = 'pointer';
      title.addEventListener('mouseenter', function() {
        this.style.textDecoration = 'underline';
      });
      title.addEventListener('mouseleave', function() {
        this.style.textDecoration = 'none';
      });

      // Click để mở link
      title.addEventListener('click', function(e) {
        e.stopPropagation(); // Ngăn event bubble lên card
        
        // Lấy URL từ card cha
        var card = title.closest('.auto-link-issue-card');
        var issueUrl = card ? card.getAttribute('data-issue-url') : null;
        
        if (issueUrl) {
          window.open(issueUrl, '_blank');
        }
      });
    });

    // Thêm event handlers cho Select All / Deselect All buttons
    var selectAllBtn = dialog.querySelector('#auto-link-select-all');
    var deselectAllBtn = dialog.querySelector('#auto-link-deselect-all');
    
    if (selectAllBtn) {
      selectAllBtn.onclick = function() {
        checkboxes.forEach(function(checkbox) {
          checkbox.checked = true;
        });
        AutoLink.updateSelectedCount(confirmBtn);
      };
    }
    
    if (deselectAllBtn) {
      deselectAllBtn.onclick = function() {
        checkboxes.forEach(function(checkbox) {
          checkbox.checked = false;
        });
        AutoLink.updateSelectedCount(confirmBtn);
      };
    }

    // Thêm event handler cho confirm button
    confirmBtn.onclick = function() {
      // Lấy danh sách issues được chọn
      var selectedIssues = [];
      checkboxes.forEach(function(checkbox) {
        if (checkbox.checked) {
          var issueId = checkbox.getAttribute('data-issue-id');
          var issue = relatedIssues.find(function(i) {
            return i.id.toString() === issueId;
          });
          if (issue) {
            selectedIssues.push(issue);
          }
        }
      });
      
      if (selectedIssues.length > 0) {
        AutoLink.confirmAutoLink(currentIssue.id, selectedIssues, overlay);
      }
    };
  };

  /**
   * Cập nhật dialog khi có kết quả từ AI Agent
   * @param {HTMLElement} overlay - Overlay element
   * @param {Object} currentIssue - Issue hiện tại
   * @param {Array} relatedIssues - Mảng issues liên quan
   * @param {string} errorMsg - Thông báo lỗi (optional)
   */
  AutoLink.updateAutoLinkPreview = function(overlay, currentIssue, relatedIssues, errorMsg) {
    var dialog = overlay.querySelector('#custom-auto-link-dialog');
    if (!dialog) return;

    var issuesContainer = dialog.querySelector('#custom-auto-link-issues-container');
    var confirmBtn = dialog.querySelector('#custom-auto-link-confirm-btn');

    // Xử lý trường hợp có lỗi
    if (errorMsg) {
      AutoLink.renderErrorState(issuesContainer, confirmBtn, errorMsg);
      return;
    }

    // Xử lý trường hợp không tìm thấy issues
    if (relatedIssues.length === 0) {
      AutoLink.renderEmptyState(issuesContainer, confirmBtn);
      return;
    }

    // Render danh sách issues
    issuesContainer.innerHTML = AutoLink.renderIssuesList(relatedIssues);
    issuesContainer.style.display = 'block';

    // Cập nhật buttons và thông tin
    AutoLink.updateDialogButtons(dialog, confirmBtn, currentIssue, relatedIssues, overlay);
  };

  /**
   * Xử lý khi tất cả requests hoàn thành
   * @param {number} successful - Số lượng requests thành công
   * @param {number} total - Tổng số requests
   * @param {Array} errors - Mảng các issue IDs bị lỗi
   * @param {HTMLElement} overlay - Overlay element
   */
  AutoLink.handleAllRelationsComplete = function(successful, total, errors, overlay) {
    document.body.removeChild(overlay);

    var message = 'Đã tự động liên kết thành công ' + successful + '/' + total + ' issue(s)!';
    if (errors.length > 0) {
      message += '\nLỗi: ' + errors.join(', ');
    }

    Utils.notify(message, successful > 0 ? 'success' : 'error', 4000);

    setTimeout(function() {
      window.location.reload();
    }, 1500);
  };

  /**
   * Tạo và gửi request để liên kết một issue
   * @param {string} currentIssueId - ID của issue hiện tại
   * @param {Object} issue - Issue cần liên kết
   * @param {string} token - CSRF token
   * @param {Function} onComplete - Callback khi request hoàn thành
   */
  AutoLink.createRelationRequest = function(currentIssueId, issue, token, onComplete) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/issues/' + currentIssueId + '/relations', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('X-CSRF-Token', token);

    xhr.onload = function() {
      var success = xhr.status === 200 || xhr.status === 201;
      onComplete(success, issue.id);
    };

    xhr.onerror = function() {
      onComplete(false, issue.id);
    };

    var relationType = 'relates';
    var params = 'utf8=✓&relation[relation_type]=' + encodeURIComponent(relationType) +
      '&relation[issue_to_id]=' + encodeURIComponent(issue.id) +
      '&authenticity_token=' + encodeURIComponent(token);
    xhr.send(params);
  };

  /**
   * Xác nhận và thực hiện liên kết các issues
   * @param {string} currentIssueId - ID của issue hiện tại
   * @param {Array} relatedIssues - Mảng các issues cần liên kết
   * @param {HTMLElement} overlay - Overlay element
   */
  AutoLink.confirmAutoLink = function(currentIssueId, relatedIssues, overlay) {
    var confirmBtn = document.getElementById('custom-auto-link-confirm-btn');
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Đang liên kết...';

    // Lấy CSRF token
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    var token = csrfToken ? csrfToken.getAttribute('content') : '';

    var completed = 0;
    var successful = 0;
    var errors = [];

    // Gửi request cho từng issue
    relatedIssues.forEach(function(issue) {
      AutoLink.createRelationRequest(currentIssueId, issue, token, function(success, issueId) {
        completed++;

        if (success) {
          successful++;
        } else {
          errors.push('#' + issueId);
        }

        // Khi tất cả requests hoàn thành
        if (completed === relatedIssues.length) {
          AutoLink.handleAllRelationsComplete(successful, relatedIssues.length, errors, overlay);
        }
      });
    });
  };

  /**
   * Khởi tạo chức năng auto link
   * Thiết lập button và các event handlers
   */
  AutoLink.init = function() {
    // Chỉ khởi tạo nếu project nằm trong danh sách bật tính năng
    if (!Utils.isProjectEnabled()) {
      return;
    }

    Utils.onReady(function() {
      AutoLink.insertAutoLinkButton();
      setTimeout(AutoLink.insertAutoLinkButton, 300);
      setTimeout(AutoLink.insertAutoLinkButton, 800);
    });

    // jQuery handlers
    if (typeof jQuery !== 'undefined') {
      jQuery(document).ready(function($) {
        $(document).ajaxComplete(function() {
          setTimeout(AutoLink.insertAutoLinkButton, 200);
        });
      });
    }
  };

  // Expose AutoLink
  window.CustomFeatures.AutoLink = AutoLink;
})();

