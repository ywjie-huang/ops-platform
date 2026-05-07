/**
 * Modal — 通用弹窗组件
 * 用法：
 *   Modal.open('modal-id')       打开
 *   Modal.close('modal-id')      关闭
 *   Modal.closeAll()             关闭所有
 *
 * HTML 结构：
 *   <div class="modal" id="xxx">
 *     <div class="modal-backdrop"></div>
 *     <div class="modal-dialog">
 *       <div class="modal-header">标题 <button class="modal-close">&times;</button></div>
 *       <div class="modal-body">内容</div>
 *     </div>
 *   </div>
 */
(function () {
  'use strict';

  function open(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('open');
    // 如果没有其他打开的 modal，恢复滚动
    if (!document.querySelector('.modal.open')) {
      document.body.style.overflow = '';
    }
  }

  function closeAll() {
    document.querySelectorAll('.modal.open').forEach(function (m) {
      m.classList.remove('open');
    });
    document.body.style.overflow = '';
  }

  // 全局事件委托
  document.addEventListener('click', function (e) {
    // 点击关闭按钮
    if (e.target.closest('.modal-close')) {
      var modal = e.target.closest('.modal');
      if (modal) close(modal.id);
      return;
    }
    // 点击背景关闭
    if (e.target.classList.contains('modal-backdrop')) {
      var modal = e.target.closest('.modal');
      if (modal) close(modal.id);
      return;
    }
  });

  // ESC 关闭
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll();
  });

  window.Modal = { open: open, close: close, closeAll: closeAll };
})();
