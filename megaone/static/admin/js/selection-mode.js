class SelectionMode {
  constructor(config) {
    this.tableSelector = config.tableSelector;
    this.toolbarId = config.toolbarId || 'selToolbar';
    this.countId = config.countId || 'selCount';
    this.idAttr = config.idAttr || 'data-row-id';
    this.checkboxSelector = config.checkboxSelector || '.sel-row-checkbox';
    this.headerCheckboxSelector = config.headerCheckboxSelector || '.sel-header-checkbox';
    this.onSelectionChange = config.onSelectionChange || null;
    this.csrfToken = config.csrfToken || this._getCsrf();
    this.deleteConfig = config.deleteConfig || null;
    this.selected = new Set();
    this._active = false;
    this._lastClicked = null;
    this._rowElements = [];
    this._longPressTimer = null;
    this._touchMoved = false;
    this._ignoreNextClick = false;
    this._init();
  }

  _getCsrf() {
    var m = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return m ? m.value : '';
  }

  _isTouchDevice() {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  }

  _init() {
    this._table = document.querySelector(this.tableSelector);
    if (!this._table) { console.warn('SelectionMode: table not found', this.tableSelector); return; }
    this._toolbar = document.getElementById(this.toolbarId);
    this._countEl = document.getElementById(this.countId);

    this._wrapCheckboxes(this._table.querySelectorAll(this.headerCheckboxSelector));
    this._wrapCheckboxes(this._table.querySelectorAll(this.checkboxSelector));
    this._rebuildRowCache();
    this._bindEvents();
    this._updateUI();

    // Ensure checkboxes start hidden
    document.body.classList.remove('sel-active');
    if (this._toolbar) this._toolbar.classList.remove('active');
  }

  _wrapCheckboxes(inputs) {
    Array.prototype.forEach.call(inputs, function (inp) {
      if (inp.parentElement && inp.parentElement.classList.contains('sel-checkbox-wrap')) return;
      var wrap = document.createElement('span');
      wrap.className = 'sel-checkbox-wrap';
      var visual = document.createElement('span');
      visual.className = 'sel-cb-visual';
      inp.parentNode.insertBefore(wrap, inp);
      wrap.appendChild(inp);
      wrap.appendChild(visual);
    });
  }

  _rebuildRowCache() {
    this._rowElements = [...this._table.querySelectorAll('tbody tr')].filter(
      function (tr) { return tr.querySelector(this.checkboxSelector); }.bind(this)
    );
  }

  // --- Activation / Deactivation ---
  _activateMode(triggerTr) {
    if (this._active) return;
    this._active = true;
    document.body.classList.add('sel-active');
    this._showCheckboxes(true);

    var id = triggerTr.getAttribute(this.idAttr);
    if (id) {
      this.selected.add(id);
      this._updateRowState(triggerTr, id);
      this._lastClicked = triggerTr;
    }
    this._updateUI();

    // Disable DataTables sort on first column while in selection mode
    this._adjustDataTableSort(false);
  }

  _deactivateMode() {
    if (!this._active) return;
    this._active = false;
    document.body.classList.remove('sel-active');

    var self = this;
    this.selected.forEach(function (id) {
      var tr = self._table.querySelector('tr[' + self.idAttr + '="' + id + '"]');
      if (tr) self._updateRowState(tr, id);
    });
    this.selected.clear();
    this._lastClicked = null;
    this._updateUI();
    this._showCheckboxes(false);
    this._adjustDataTableSort(true);
  }

  _showCheckboxes(show) {
    var wraps = this._table.querySelectorAll('.sel-cb-visual');
    Array.prototype.forEach.call(wraps, function (el) {
      el.style.opacity = show ? '1' : '0';
      el.style.transform = show ? 'scale(1)' : 'scale(0.5)';
      el.style.pointerEvents = show ? 'auto' : 'none';
    });
    var inputs = this._table.querySelectorAll(this.checkboxSelector + ', ' + this.headerCheckboxSelector);
    Array.prototype.forEach.call(inputs, function (el) {
      el.style.opacity = show ? '1' : '0';
      el.style.pointerEvents = show ? 'auto' : 'none';
    });
  }

  _adjustDataTableSort(enable) {
    if (!this._table) return;
    try {
      var dt = $.fn.dataTable ? $(this._table).DataTable() : null;
      if (dt) {
        dt.settings()[0].aoColumns[0].bSortable = enable;
      }
    } catch (e) { /* no DataTable or different config */ }
  }

  // --- Event Binding ---
  _bindEvents() {
    var self = this;
    var isTouch = this._isTouchDevice();

    // Prevent browser context menu on table rows
    this._table.addEventListener('contextmenu', function (e) {
      var tr = e.target.closest('tr');
      if (tr && tr.closest('tbody')) {
        e.preventDefault();
        self._ignoreNextClick = true;
        if (!self._active) {
          self._activateMode(tr);
        } else {
          self._rowClickHandler(tr, e.shiftKey);
        }
      }
    });

    // Row click: if in selection mode, toggle; otherwise let normal clicks pass
    this._table.addEventListener('click', function (e) {
      if (self._ignoreNextClick) { self._ignoreNextClick = false; return; }
      // Don't intercept clicks inside action buttons/links
      if (e.target.closest('a, button, .btn, input:not(' + self.checkboxSelector + '), select, textarea')) return;
      var tr = e.target.closest('tr');
      if (tr && tr.closest('tbody')) {
        if (self._active) {
          e.preventDefault();
          self._rowClickHandler(tr, e.shiftKey);
        }
      }
    });

    // Touch long-press (mobile)
    if (isTouch) {
      this._table.addEventListener('touchstart', function (e) {
        self._touchMoved = false;
        var tr = e.target.closest('tr');
        if (!tr || !tr.closest('tbody')) return;
        if (e.target.closest('a, button, .btn, input, select, textarea')) return;
        self._longPressTimer = setTimeout(function () {
          if (!self._touchMoved) {
            navigator.vibrate && navigator.vibrate(15);
            if (!self._active) {
              self._activateMode(tr);
            } else {
              self._rowClickHandler(tr, false);
            }
          }
        }, 450);
      }, { passive: true });

      this._table.addEventListener('touchmove', function () {
        self._touchMoved = true;
        if (self._longPressTimer) {
          clearTimeout(self._longPressTimer);
          self._longPressTimer = null;
        }
      }, { passive: true });

      this._table.addEventListener('touchend', function () {
        if (self._longPressTimer) {
          clearTimeout(self._longPressTimer);
          self._longPressTimer = null;
        }
      }, { passive: true });
    }

    // Checkbox change events (for actual checkbox clicks too)
    this._table.addEventListener('change', function (e) {
      var cb = e.target.closest(self.checkboxSelector);
      if (!cb) return;
      var tr = cb.closest('tr');
      if (!tr) return;
      var id = tr.getAttribute(self.idAttr);
      if (!id) return;
      if (!self._active) {
        self._activateMode(tr);
      } else {
        self._rowClickHandler(tr, e.shiftKey);
      }
    });

    // Header checkbox
    var headerCb = this._table.querySelector(this.headerCheckboxSelector);
    if (headerCb) {
      headerCb.addEventListener('change', function () {
        if (this.checked) {
          self.selectAllVisible();
        } else {
          self.clearSelection();
          if (self.selected.size === 0) self._deactivateMode();
        }
      });
    }

    // Toolbar buttons
    if (this._toolbar) {
      var selectAllBtn = this._toolbar.querySelector('[data-sel-action="select-all"]');
      if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function () { self.selectAllVisible(); });
      }
      var clearBtn = this._toolbar.querySelector('[data-sel-action="clear"]');
      if (clearBtn) {
        clearBtn.addEventListener('click', function () {
          self.clearSelection();
          if (self.selected.size === 0) self._deactivateMode();
        });
      }
      var deleteBtn = this._toolbar.querySelector('[data-sel-action="bulk-delete"]');
      if (deleteBtn) {
        deleteBtn.addEventListener('click', function () {
          if (self.deleteConfig) {
            var opts = Object.assign({}, self.deleteConfig.opts || {});
            self.bulkDelete(self.deleteConfig.url, opts, self.deleteConfig.cb);
          } else {
            self.triggerDeleteFallback();
          }
        });
      }
      var exitBtn = this._toolbar.querySelector('[data-sel-action="exit"]');
      if (exitBtn) {
        exitBtn.addEventListener('click', function () { self._deactivateMode(); });
      }
    }

    // Keyboard: Escape closes confirm dialog only (handled by Bootstrap keyboard:true)
  }

  _rowClickHandler(tr, shiftKey) {
    var id = tr.getAttribute(this.idAttr);
    if (!id) return;

    // Shift+Click range selection
    if (shiftKey && this._lastClicked) {
      this._selectRange(this._lastClicked, tr);
      return;
    }

    if (this.selected.has(id)) {
      this.selected.delete(id);
      this._updateRowState(tr, id);
      if (this.selected.size === 0) {
        this._deactivateMode();
        return;
      }
    } else {
      this.selected.add(id);
      this._updateRowState(tr, id);
    }
    this._lastClicked = tr;
    this._updateUI();
  }

  _toggle(id, tr) {
    if (this.selected.has(id)) {
      this.selected.delete(id);
    } else {
      this.selected.add(id);
    }
    this._updateRowState(tr, id);
    this._updateUI();
  }

  _selectRange(fromTr, toTr) {
    var rows = this._rowElements;
    var startIdx = rows.indexOf(fromTr);
    var endIdx = rows.indexOf(toTr);
    if (startIdx === -1 || endIdx === -1) return;
    var min = Math.min(startIdx, endIdx);
    var max = Math.max(startIdx, endIdx);
    for (var i = min; i <= max; i++) {
      var tr = rows[i];
      var id = tr.getAttribute(this.idAttr);
      if (id && !this.selected.has(id)) {
        this.selected.add(id);
        this._updateRowState(tr, id);
      }
    }
    this._updateUI();
  }

  _updateRowState(tr, id) {
    var cb = tr.querySelector(this.checkboxSelector);
    if (cb) cb.checked = this.selected.has(id);
    tr.classList.toggle('sel-row-selected', this.selected.has(id));
  }

  _updateUI() {
    var count = this.selected.size;
    if (this._countEl) {
      this._countEl.innerHTML = '<strong>' + count + '</strong> item' + (count !== 1 ? 's' : '') + ' selected';
    }
    if (this._toolbar) {
      this._toolbar.classList.toggle('active', this._active && count > 0);
    }

    var headerCb = this._table && this._table.querySelector(this.headerCheckboxSelector);
    if (headerCb) {
      var visible = this._rowElements.filter(function (tr) { return tr.style.display !== 'none'; });
      var self = this;
      var checked = visible.filter(function (tr) {
        return self.selected.has(tr.getAttribute(self.idAttr));
      });
      if (visible.length > 0 && checked.length === visible.length) {
        headerCb.checked = true;
        headerCb.indeterminate = false;
      } else if (checked.length > 0) {
        headerCb.checked = false;
        headerCb.indeterminate = true;
      } else {
        headerCb.checked = false;
        headerCb.indeterminate = false;
      }
    }

    if (this.onSelectionChange) this.onSelectionChange(this.selected, count);
    var event = new CustomEvent('selectionChange', { detail: { active: this._active, selected: this.selected, count: count } });
    document.dispatchEvent(event);
  }

  // --- Public API ---
  selectAllVisible() {
    var self = this;
    this._rowElements.forEach(function (tr) {
      if (tr.style.display === 'none') return;
      var id = tr.getAttribute(self.idAttr);
      if (id) {
        self.selected.add(id);
        self._updateRowState(tr, id);
      }
    });
    this._updateUI();
  }

  clearSelection() {
    var self = this;
    this.selected.forEach(function (id) {
      var tr = self._table.querySelector('tr[' + self.idAttr + '="' + id + '"]');
      if (tr) self._updateRowState(tr, id);
    });
    this.selected.clear();
    this._lastClicked = null;
    this._updateUI();
  }

  triggerDeleteFallback() {
    var event = new CustomEvent('selBulkDelete', { detail: { ids: this.getSelectedIds() } });
    document.dispatchEvent(event);
  }

  getSelected() { return new Set(this.selected); }
  getSelectedIds() { return [...this.selected]; }
  getSelectedCount() { return this.selected.size; }
  isActive() { return this._active; }

  refresh() {
    this._wrapCheckboxes(this._table.querySelectorAll(this.headerCheckboxSelector));
    this._wrapCheckboxes(this._table.querySelectorAll(this.checkboxSelector));
    this._rebuildRowCache();
    var self = this;
    this._rowElements.forEach(function (tr) {
      var id = tr.getAttribute(self.idAttr);
      if (id && self.selected.has(id)) {
        self._updateRowState(tr, id);
      }
    });
    this._showCheckboxes(this._active);
    this._updateUI();
  }

  destroy() {
    this._deactivateMode();
    this.selected = null;
    this._table = null;
    this._toolbar = null;
    this._countEl = null;
    this._rowElements = null;
  }
}

// --- Prototype helpers ---
SelectionMode.prototype.addExtraAction = function (label, icon, className, callback) {
  var container = document.getElementById('selExtraActions');
  if (!container) return;
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'sel-btn ' + (className || '');
  btn.innerHTML = (icon ? '<i class="bi bi-' + icon + ' me-1"></i>' : '') + label;
  var self = this;
  btn.addEventListener('click', function () { callback(self.getSelectedIds()); });
  container.appendChild(btn);
};

SelectionMode.prototype.bulkDelete = function (url, opts, cb) {
  var self = this;
  var ids = this.getSelectedIds();
  if (!ids.length) return;
  opts = opts || {};
  var count = ids.length;
  var title = opts.title || 'Delete selected item(s)?';
  var msg = opts.message || 'This will permanently delete ' + count + ' item' + (count !== 1 ? 's' : '') + '.';
  var okText = opts.okText || 'Delete';
  confirmAction(msg, title, okText).then(function (r) {
    if (!r) return;
    var body = { model: opts.model || '', action: 'delete', ids: ids };
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': self.csrfToken },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (data.success) {
        self._deactivateMode();
        location.reload();
      } else {
        alert(data.error || 'Delete failed. Please try again.');
      }
      if (cb) cb(data);
    }).catch(function (e) {
      alert('Error: ' + e.message);
      if (cb) cb({ error: e.message });
    });
  });
};

SelectionMode.prototype.bulkExport = function (url) {
  var ids = this.getSelectedIds();
  if (!ids.length) return;
  var form = document.createElement('form');
  form.method = 'POST';
  form.action = url;
  var csrf = document.createElement('input');
  csrf.type = 'hidden';
  csrf.name = 'csrfmiddlewaretoken';
  csrf.value = this.csrfToken;
  form.appendChild(csrf);
  ids.forEach(function (id) {
    var inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = 'ids';
    inp.value = id;
    form.appendChild(inp);
  });
  document.body.appendChild(form);
  form.submit();
};

window.SelectionMode = SelectionMode;
