/*
 * Offline support for the Hebrew reader: registers the service worker and
 * drives the "Download all" / "Update" button in the toolbar.
 *
 * Downloads go into a brand-new cache. Only when every file has arrived is the
 * old cache deleted, so a failed or interrupted update never leaves you with a
 * half-working offline copy.
 */
(function () {
  'use strict';

  var PREFIX = 'hebrew-reader-';
  var KEY = 'hebrew-reader-offline'; // localStorage: {cache, version, date, bytes}
  var CONCURRENCY = 4;

  var bar = document.getElementById('app-bar');
  if (!bar) return;
  var statusEl = document.getElementById('ab-status');
  var button = document.getElementById('ab-button');

  if (!('serviceWorker' in navigator) || !('caches' in window)) {
    statusEl.textContent = 'Offline use is not supported in this browser.';
    button.hidden = true;
    return;
  }

  var busy = false;

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; }
  }
  function save(v) {
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { /* storage blocked */ }
  }
  function mb(bytes) { return (bytes / 1048576).toFixed(1) + ' MB'; }
  function setButton(label, show) {
    button.textContent = label;
    button.hidden = !show;
  }

  function showSaved(remote) {
    var s = load();
    if (s && s.cache) {
      var when = new Date(s.date).toLocaleDateString();
      if (remote && remote.version !== s.version) {
        statusEl.textContent = 'Update available (downloaded ' + when + ')';
        bar.classList.add('ab-attention');
      } else {
        statusEl.textContent = 'Available offline · downloaded ' + when;
        bar.classList.remove('ab-attention');
      }
      setButton('Update', true);
    } else {
      statusEl.textContent = remote
        ? 'Not saved for offline use (' + mb(remote.total) + ')'
        : 'Not saved for offline use';
      setButton('Download all', true);
    }
  }

  function fetchList() {
    return fetch('files.json', { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('files.json: HTTP ' + r.status);
      return r.json();
    }).then(function (list) {
      list.total = list.files.reduce(function (n, f) { return n + f.size; }, 0);
      return list;
    });
  }

  function downloadAll() {
    if (busy) return Promise.resolve();
    if (!navigator.onLine) {
      statusEl.textContent = 'You are offline. Connect to the internet to download.';
      return Promise.resolve();
    }
    busy = true;
    setButton('', false);
    statusEl.textContent = 'Checking for files…';
    var previous = load();
    var name = PREFIX + String(Date.now()).padStart(13, '0');
    var list, cache, done = 0, bytes = 0, failed = false;

    if (navigator.storage && navigator.storage.persist) {
      navigator.storage.persist().catch(function () {});
    }

    return fetchList().then(function (l) {
      list = l;
      return caches.open(name);
    }).then(function (c) {
      cache = c;
      var queue = list.files.slice();
      function progress() {
        if (failed) return;
        statusEl.textContent = 'Downloading ' + done + ' / ' + list.files.length +
          ' (' + mb(bytes) + ' of ' + mb(list.total) + ')';
      }
      progress();
      function worker() {
        var f = failed ? null : queue.shift();
        if (!f) return Promise.resolve();
        var url = new URL(f.url, document.baseURI).href;
        // cache: 'reload' skips the browser's HTTP cache so we really get the server's copy.
        return fetch(url, { cache: 'reload' }).then(function (res) {
          if (!res.ok) { failed = true; throw new Error(f.url + ': HTTP ' + res.status); }
          return cache.put(url, res);
        }).then(function () {
          done += 1;
          bytes += f.size;
          progress();
          return worker();
        });
      }
      var workers = [];
      for (var i = 0; i < CONCURRENCY; i++) workers.push(worker());
      return Promise.all(workers);
    }).then(function () {
      // Everything arrived: drop every other copy, keep the new one.
      return caches.keys().then(function (names) {
        return Promise.all(names.filter(function (n) {
          return n.indexOf(PREFIX) === 0 && n !== name;
        }).map(function (n) { return caches.delete(n); }));
      });
    }).then(function () {
      save({ cache: name, version: list.version, date: Date.now(), bytes: list.total });
      busy = false;
      // Pick up a new service worker too, then show the fresh copy of this page.
      return navigator.serviceWorker.getRegistration().then(function (reg) {
        return reg ? reg.update().catch(function () {}) : null;
      }).then(function () {
        statusEl.textContent = 'Done. Reloading…';
        location.reload();
      });
    }).catch(function (err) {
      failed = true;
      busy = false;
      caches.delete(name);
      console.error(err);
      statusEl.textContent = (previous ? 'Update failed; your previous offline copy is still in place. '
                                       : 'Download failed. ') + 'Please try again.';
      setButton(previous ? 'Update' : 'Download all', true);
    });
  }

  button.addEventListener('click', function (e) {
    e.stopPropagation();
    var s = load();
    if (s && s.cache && !confirm('Clear the offline copy and download everything again from the server?')) return;
    downloadAll();
  });

  navigator.serviceWorker.register('sw.js').catch(function (err) {
    console.error('Service worker registration failed', err);
  });

  showSaved(null);
  var installed = window.matchMedia('(display-mode: standalone)').matches ||
                  window.navigator.standalone === true;

  if (navigator.onLine) {
    fetchList().then(function (remote) {
      showSaved(remote);
      // Installed to the home screen but never downloaded: fetch everything now.
      if (installed && !load()) downloadAll();
    }).catch(function () { /* offline or server unreachable: keep local status */ });
  }
})();
