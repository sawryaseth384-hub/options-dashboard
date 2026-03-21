const axios = require('axios');
require('dotenv').config(); // For environment variables

const BASE_URL = "https://api.dhan.co/v2";

// ========================= 
// 🔐 HEADERS 
// =========================
function getHeaders() {
  return {
    "access-token": process.env.ACCESS_TOKEN,
    "client-id": process.env.CLIENT_ID,
    "Content-Type": "application/json"
  };
}

// ========================= 
// 🔄 SEGMENT → EXCHANGE MAP 
// =========================
function mapExchange(segment) {
  // Index (NIFTY / BANKNIFTY)
  if (segment === "IDX_I") {
    return "NSE_EQ";
  }
  // Stocks / FNO
  return "NSE_FNO";
}

// ========================= 
// 🧪 DEBUG TOGGLE 
// =========================
function debugLog(label, data, isDebugEnabled = false) {
  if (isDebugEnabled) {
    console.log(`${label}:`, data);
  }
}

// ========================= 
// 💰 LTP (Last Price) 
// =========================
async function getLtp(securityId, segment, isDebugEnabled = false) {
  const exchange = mapExchange(segment);
  
  const payload = {
    "NSE_EQ": [],
    "NSE_FNO": []
  };
  
  payload[exchange].push(parseInt(securityId));
  
  try {
    const response = await axios.post(
      `${BASE_URL}/marketfeed/ltp`,
      payload,
      { headers: getHeaders(), timeout: 10000 }
    );
    
    const data = response.data;
    debugLog("LTP RAW", data, isDebugEnabled);
    
    return data?.data?.[exchange]?.[securityId]?.last_price || 0;
  } catch (error) {
    console.error(`LTP Error: ${error.message}`);
    return 0;
  }
}

// ========================= 
// 📊 OHLC DATA 
// =========================
async function getOhlc(securityId, segment, isDebugEnabled = false) {
  const exchange = mapExchange(segment);
  
  const payload = {
    "NSE_EQ": [],
    "NSE_FNO": []
  };
  
  payload[exchange].push(parseInt(securityId));
  
  try {
    const response = await axios.post(
      `${BASE_URL}/marketfeed/ohlc`,
      payload,
      { headers: getHeaders(), timeout: 10000 }
    );
    
    const data = response.data;
    debugLog("OHLC RAW", data, isDebugEnabled);
    
    return data?.data?.[exchange]?.[securityId] || {};
  } catch (error) {
    console.error(`OHLC Error: ${error.message}`);
    return {};
  }
}

// ========================= 
// 📊 FULL QUOTE (Market Depth) 
// =========================
async function getQuote(securityId, segment, isDebugEnabled = false) {
  const exchange = mapExchange(segment);
  
  const payload = {
    "NSE_EQ": [],
    "NSE_FNO": []
  };
  
  payload[exchange].push(parseInt(securityId));
  
  try {
    const response = await axios.post(
      `${BASE_URL}/marketfeed/quote`,
      payload,
      { headers: getHeaders(), timeout: 10000 }
    );
    
    const data = response.data;
    debugLog("QUOTE RAW", data, isDebugEnabled);
    
    return data?.data?.[exchange]?.[securityId] || {};
  } catch (error) {
    console.error(`Quote Error: ${error.message}`);
    return {};
  }
}

// Example usage
async function main() {
  const securityId = "49081"; // Example security ID
  const segment = "NSE_FNO";
  
  console.log("Getting LTP...");
  const ltp = await getLtp(securityId, segment, true);
  console.log("LTP:", ltp);
  
  console.log("Getting OHLC...");
  const ohlc = await getOhlc(securityId, segment, true);
  console.log("OHLC:", ohlc);
  
  console.log("Getting Quote...");
  const quote = await getQuote(securityId, segment, true);
  console.log("Quote:", quote);
}

// Uncomment to run the example
// main().catch(console.error);

module.exports = {
  getLtp,
  getOhlc,
  getQuote,
  mapExchange,
  getHeaders
};
