/**
 * TableKit — 前端表格排序 + 分页
 * 用法：table-wrap[data-table="true"][data-page-size="10"]
 */
(function () {
  'use strict';

  var DEFAULT_PAGE_SIZE = 10;
  var DEFAULT_PAGE_SIZES = [10, 20, 50, 100];

  function initAll() {
    document.querySelectorAll('.table-wrap[data-table]').forEach(initTable);
  }

  function initTable(wrap) {
    var table = wrap.querySelector('table');
    if (!table) return;
    var thead = table.querySelector('thead');
    var tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;

    var headers = Array.from(thead.querySelectorAll('th'));
    var allRows = Array.from(tbody.querySelectorAll('tr'));
    var originalRows = allRows.filter(function (r) { return !r.querySelector('.table-empty'); });
    if (originalRows.length === 0) return;

    var pageSize = parseInt(wrap.dataset.pageSize, 10) || DEFAULT_PAGE_SIZE;
    var pageSizes = (wrap.dataset.pageSizes || '').split(',').map(Number).filter(Boolean);
    var sizes = pageSizes.length ? pageSizes : DEFAULT_PAGE_SIZES;

    headers.forEach(function (th, idx) {
      if (th.dataset.sort === 'false') return;
      th.classList.add('sortable');
      th.dataset.col = idx;
    });

    var sortCol = -1;
    var sortDir = 'asc';
    var currentPage = 1;

    function getCellValue(row, colIdx) {
      var td = row.children[colIdx];
      return td ? td.textContent.trim() : '';
    }

    function compareValues(a, b) {
      var na = parseFloat(a), nb = parseFloat(b);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return a.localeCompare(b, 'zh-CN', { numeric: true });
    }

    function sortRows(rows) {
      if (sortCol < 0) return rows;
      return rows.slice().sort(function (a, b) {
        var cmp = compareValues(getCellValue(a, sortCol), getCellValue(b, sortCol));
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }

    function getTotalPages(n) { return Math.max(1, Math.ceil(n / pageSize)); }
    function getPageRows(rows) { var s = (currentPage - 1) * pageSize; return rows.slice(s, s + pageSize); }

    function render() {
      var sorted = sortRows(originalRows);
      var totalPages = getTotalPages(sorted.length);
      if (currentPage > totalPages) currentPage = totalPages;
      var pageRows = getPageRows(sorted);

      headers.forEach(function (th) {
        th.classList.remove('sort-asc', 'sort-desc');
        if (parseInt(th.dataset.col, 10) === sortCol) {
          th.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
      });

      tbody.innerHTML = '';
      pageRows.forEach(function (r) { tbody.appendChild(r); });

      renderFooter(sorted.length, totalPages);
    }

    function renderFooter(total, totalPages) {
      var footer = wrap.parentNode.querySelector('.table-foot');
      if (!footer) {
        footer = document.createElement('div');
        footer.className = 'table-foot';
        wrap.parentNode.insertBefore(footer, wrap.nextSibling);
      }

      var start = (currentPage - 1) * pageSize + 1;
      var end = Math.min(currentPage * pageSize, total);

      if (totalPages <= 1) {
        footer.innerHTML = '<div class="table-info">共 ' + total + ' 条记录</div><div></div>';
        return;
      }

      footer.innerHTML =
        '<div class="table-info">共 <strong>' + total + '</strong> 条，第 ' + start + '-' + end + ' 条</div>' +
        '<div style="display:flex;align-items:center;gap:12px;">' +
          '<label class="page-size-select" style="font-size:12px;color:var(--text-sub);display:flex;align-items:center;gap:4px;">' +
            '每页 <select data-role="page-size" style="height:26px;padding:0 6px;border:1px solid var(--border);border-radius:4px;font-size:12px;">' +
              sizes.map(function (s) { return '<option value="' + s + '"' + (s === pageSize ? ' selected' : '') + '>' + s + '</option>'; }).join('') +
            '</select> 条' +
          '</label>' +
          '<div class="pagination" data-role="pagination">' + buildPagination(currentPage, totalPages) + '</div>' +
        '</div>';

      var sizeSelect = footer.querySelector('[data-role="page-size"]');
      sizeSelect.addEventListener('change', function () {
        pageSize = parseInt(sizeSelect.value, 10) || DEFAULT_PAGE_SIZE;
        wrap.dataset.pageSize = pageSize;
        currentPage = 1;
        render();
      });

      footer.querySelectorAll('.pagination button[data-page]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var p = parseInt(btn.dataset.page, 10);
          if (p >= 1 && p <= totalPages) { currentPage = p; render(); }
        });
      });
    }

    function buildPagination(cur, total) {
      if (total <= 1) return '';
      var pages = [];
      pages.push('<button data-page="' + (cur - 1) + '"' + (cur === 1 ? ' disabled' : '') + '>‹</button>');
      if (total <= 7) {
        for (var i = 1; i <= total; i++) pages.push('<button data-page="' + i + '"' + (i === cur ? ' aria-current="page"' : '') + '>' + i + '</button>');
      } else {
        pages.push('<button data-page="1"' + (cur === 1 ? ' aria-current="page"' : '') + '>1</button>');
        if (cur > 3) pages.push('<span class="page-ellipsis">…</span>');
        var s = Math.max(2, cur - 1), e = Math.min(total - 1, cur + 1);
        for (var j = s; j <= e; j++) pages.push('<button data-page="' + j + '"' + (j === cur ? ' aria-current="page"' : '') + '>' + j + '</button>');
        if (cur < total - 2) pages.push('<span class="page-ellipsis">…</span>');
        pages.push('<button data-page="' + total + '"' + (cur === total ? ' aria-current="page"' : '') + '>' + total + '</button>');
      }
      pages.push('<button data-page="' + (cur + 1) + '"' + (cur === total ? ' disabled' : '') + '>›</button>');
      return pages.join('');
    }

    thead.addEventListener('click', function (e) {
      var th = e.target.closest('th.sortable');
      if (!th) return;
      var col = parseInt(th.dataset.col, 10);
      if (sortCol === col) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
      else { sortCol = col; sortDir = 'asc'; }
      currentPage = 1;
      render();
    });

    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
