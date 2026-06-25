// Shared dashboard logic for Bancroft Air.
// Each template injects window.BANCROFT (nodes, labels, sensor maps, status
// thresholds, stale_seconds) before loading this file, so nothing here is hardcoded.
(function () {
  const B = window.BANCROFT || {};
  const TH = B.status_thresholds || { co2: [800, 1000, 1500], pm25: [12, 35, 55] };
  const ECO2_NODES = B.eco2_nodes || [];

  // Milliseconds after which a node's last reading is treated as offline.
  window.STALE_MS = (B.stale_seconds || 300) * 1000;

  // GOOD / OK / POOR / BAD / OFFLINE colour bands. The dashboard map/list use the
  // face + dotBg keys; the room detail page uses the label key. Hex is identical
  // across both pages.
  window.STATUS_PALETTE = {
    GOOD:    { bg:'#e9f7ee', text:'#5a8a6c', num:'#2f7d52', dotBg:'#c4ead2', face:'check', label:'Good'    },
    OK:      { bg:'#fcefd8', text:'#9d7530', num:'#a56b15', dotBg:'#f2d8a0', face:'flat',  label:'OK'      },
    POOR:    { bg:'#fcdecb', text:'#ad5c28', num:'#ac4810', dotBg:'#f3c08a', face:'alert', label:'Poor'    },
    BAD:     { bg:'#f9d2ce', text:'#a83530', num:'#b52520', dotBg:'#eeaaa6', face:'alert', label:'Bad'     },
    OFFLINE: { bg:'#f3f1ed', text:'#b3aa9e', num:'#b3aa9e', dotBg:'#e6e0d6', face:'off',   label:'Offline' },
  };

  // Classify a node's latest reading into a STATUS_PALETTE key.
  // ECO₂ nodes (kitchen) are judged on PM2.5; every other node on CO₂.
  window.nodeStatus = function (node, data) {
    if (!data || !data.timestamp) return 'OFFLINE';
    if (Date.now() - new Date(data.timestamp).getTime() > window.STALE_MS) return 'OFFLINE';
    const usePm = ECO2_NODES.includes(node);
    const bands = usePm ? TH.pm25 : TH.co2;
    const v     = usePm ? data.pm25 : data.co2_ppm;
    if (v == null) return 'OFFLINE';
    if (v < bands[0]) return 'GOOD';
    if (v < bands[1]) return 'OK';
    if (v < bands[2]) return 'POOR';
    return 'BAD';
  };

  // Short relative-age label for a timestamp ("12s", "4m", "old", "offline").
  window.relAge = function (ts, stale) {
    if (stale || !ts) return 'offline';
    const diff = Date.now() - new Date(ts).getTime();
    if (diff < 0 || isNaN(diff)) return '';
    if (diff < 60000)   return Math.round(diff / 1000) + 's';
    if (diff < 3600000) return Math.round(diff / 60000) + 'm';
    return 'old';
  };
})();
