const dns = require("node:dns");
dns.setDefaultResultOrder("ipv4first");
const originalLookup = dns.lookup;
dns.lookup = function (hostname, options, callback) {
  if (typeof options === "function") {
    callback = options;
    options = {};
  }
  return originalLookup.call(this, hostname, { ...options, family: 4 }, callback);
};
