/**
 * FilterBar — 搜索栏交互增强
 * - 搜索框有内容时显示清除按钮
 * - checkbox 切换 active 样式
 */
(function () {
  'use strict';

  function init() {
    // 清除按钮：输入时显示/隐藏
    document.querySelectorAll('.filter-search input').forEach(input => {
      const clearBtn = input.parentNode.querySelector('.filter-search-clear');
      if (!clearBtn) return;

      // 已有值时显示
      if (input.value.trim()) clearBtn.classList.add('visible');

      input.addEventListener('input', () => {
        clearBtn.classList.toggle('visible', input.value.trim().length > 0);
      });
    });

    // Checkbox active 状态
    document.querySelectorAll('.filter-check input[type="checkbox"]').forEach(cb => {
      const label = cb.closest('.filter-check');
      if (!label) return;

      const update = () => label.classList.toggle('active', cb.checked);
      update();
      cb.addEventListener('change', update);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
