/**
 * Toast — 操作反馈提示组件
 * 通过 cookie（ops_toast / ops_toast_type）传递消息
 * 备用：也支持 URL 参数 ?toast=消息&type=success|error|info
 * JS 手动调用：Toast.show('消息', 'success')
 */
(function () {
  'use strict';

  var DURATION = 4000;

  function show(message, type) {
    type = type || 'info';
    var container = getContainer();
    var el = document.createElement('div');
    el.className = 'toast toast-' + type;

    var icons = {
      success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>',
      error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    el.innerHTML =
      '<span class="toast-icon">' + (icons[type] || icons.info) + '</span>' +
      '<span class="toast-msg">' + escapeHtml(message) + '</span>' +
      '<button class="toast-close" aria-label="close">&times;</button>';

    el.querySelector('.toast-close').addEventListener('click', function () {
      dismiss(el);
    });

    container.appendChild(el);
    requestAnimationFrame(function () {
      el.classList.add('toast-visible');
    });

    setTimeout(function () {
      dismiss(el);
    }, DURATION);
  }

  function dismiss(el) {
    if (el._dismissed) return;
    el._dismissed = true;
    el.classList.remove('toast-visible');
    el.classList.add('toast-exit');
    setTimeout(function () {
      el.remove();
    }, 300);
  }

  function getContainer() {
    var c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function deleteCookie(name) {
    document.cookie = name + '=; path=/; max-age=0';
  }

  function autoDetect() {
    // 优先从 cookie 读取
    var msg = getCookie('ops_toast');
    if (msg) {
      var type = getCookie('ops_toast_type') || 'success';
      deleteCookie('ops_toast');
      deleteCookie('ops_toast_type');
      show(msg, type);
      return;
    }
    // 备用：从 URL 参数读取
    var params = new URLSearchParams(window.location.search);
    var urlMsg = params.get('toast');
    if (urlMsg) {
      show(urlMsg, params.get('type') || 'success');
      params.delete('toast');
      params.delete('type');
      var newUrl = window.location.pathname;
      var qs = params.toString();
      if (qs) newUrl += '?' + qs;
      window.history.replaceState({}, '', newUrl);
    }
  }

  window.Toast = { show: show };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoDetect);
  } else {
    autoDetect();
  }
})();
