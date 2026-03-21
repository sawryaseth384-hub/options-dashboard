const axios = require('axios');
const moment = require('moment');

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
// 📈 GET HISTORICAL DATA
// =========================
async function getHistorical(securityId, segment) {

    const url = `${BASE_URL}/charts/intraday`;

    const toDate = moment();
    const fromDate = moment().subtract(1, 'days');

    const payload = {
        securityId: String(securityId),
        exchangeSegment: segment,

        // 🔥 CRITICAL FIX
        instrument: segment === "IDX_I" ? "INDEX" : "EQUITY",

        interval: "5",
        oi: false,
        fromDate: fromDate.format("YYYY-MM-DD HH:mm:ss"),
        toDate: toDate.format("YYYY-MM-DD HH:mm:ss")
    };

    try {
        const response = await axios.post(url, payload, {
            headers: getHeaders(),
            timeout: 10000
        });

        const res = response.data;

        // =========================
        // ❌ ERROR CHECK
        // =========================
        if (!res || res.status === "failure" || !res.data) {
            console.log("❌ Invalid API response:", res);
            return [];
        }

        const d = res.data;

        if (!d.timestamp || !d.open) {
            return [];
        }

        // =========================
        // ✅ FORMAT DATA
        // =========================
        const result = d.timestamp.map((ts, i) => ({
            time: new Date(ts * 1000),   // ✅ FIX (human readable)
            open: d.open[i],
            high: d.high[i],
            low: d.low[i],
            close: d.close[i],
            volume: d.volume ? d.volume[i] : 0
        }));

        return result;

    } catch (error) {
        console.error("❌ Historical API Error:", error.response?.data || error.message);
        return [];
    }
}

// =========================
// 🚀 TEST
// =========================
async function main() {
    const data = await getHistorical(13, "IDX_I"); // NIFTY

    console.log("📊 DATA SAMPLE:");
    console.log(data.slice(0, 3));
}

if (require.main === module) {
    main();
}

module.exports = { getHistorical };
