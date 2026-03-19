<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pro Trading Dashboard</title>

<!-- Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">

<!-- Icons -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">

<!-- Chart -->
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>

<style>

body{
    margin:0;
    font-family:'Inter';
    background:#0B0E11;
    color:white;
}

/* ===== TICKER ===== */
.ticker{
    background:#111;
    padding:8px;
    overflow:hidden;
}

.ticker-track{
    white-space:nowrap;
    display:inline-block;
    animation:scroll 20s linear infinite;
}

.ticker-item{
    margin-right:30px;
    display:inline-block;
    font-size:13px;
}

@keyframes scroll{
    from{transform:translateX(0);}
    to{transform:translateX(-100%);}
}

/* ===== HEADER ===== */
.header{
    display:flex;
    justify-content:space-between;
    padding:10px 20px;
    background:#1C1F26;
}

/* ===== LAYOUT ===== */
.container{
    display:grid;
    grid-template-columns:200px 1fr;
}

.sidebar{
    background:#1C1F26;
    height:100vh;
    padding:20px;
}

.sidebar div{
    margin:12px 0;
    cursor:pointer;
}

.main{
    padding:20px;
}

/* ===== CARDS ===== */
.cards{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:10px;
}

.card{
    background:#1C1F26;
    padding:15px;
    border-radius:10px;
}

/* ===== CHART ===== */
.chart-box{
    background:#1C1F26;
    margin-top:15px;
    padding:15px;
    border-radius:10px;
}

/* ===== TABLE ===== */
table{
    width:100%;
    margin-top:15px;
}

td,th{
    padding:8px;
    border-bottom:1px solid #333;
}

.green{color:#00C076;}
.red{color:#F6465D;}

</style>
</head>

<body>

<!-- 🔥 TICKER -->
<div class="ticker">
    <div class="ticker-track" id="tickerData"></div>
</div>

<!-- HEADER -->
<div class="header">
    <div>📊 Pro Dashboard</div>
    <div>🔍 Search</div>
    <div><i class="fa fa-bell"></i> <i class="fa fa-user"></i></div>
</div>

<div class="container">

<!-- SIDEBAR -->
<div class="sidebar">
    <div>Home</div>
    <div>Markets</div>
    <div>Portfolio</div>
    <div>Orders</div>
    <div>Watchlist</div>
</div>

<!-- MAIN -->
<div class="main">

<!-- CARDS -->
<div class="cards">
    <div class="card">Net Worth<br><b>₹5,00,000</b></div>
    <div class="card">P&L<br><b class="green">+₹8,000</b></div>
    <div class="card">Margin<br><b>₹1,20,000</b></div>
    <div class="card">Buying Power<br><b>₹3,00,000</b></div>
</div>

<!-- CHART -->
<div class="chart-box">
    <div id="chart" style="height:300px;"></div>
</div>

<!-- WATCHLIST -->
<div class="card">
<h3>Watchlist</h3>
<table>
<tr><th>Stock</th><th>LTP</th><th>Change</th></tr>
<tr><td>NIFTY</td><td>23700</td><td class="green">+120</td></tr>
<tr><td>BANKNIFTY</td><td>55200</td><td class="green">+300</td></tr>
<tr><td>RELIANCE</td><td>2900</td><td class="red">-20</td></tr>
</table>
</div>

</div>
</div>

<script>

// 🔥 TICKER DATA
const tickerData = [
    {name:"NIFTY",price:23700,change:120},
    {name:"BANKNIFTY",price:55200,change:300},
    {name:"SENSEX",price:78500,change:250},
    {name:"VIX",price:18.2,change:-0.5}
];

// 🔥 LOAD TICKER
function loadTicker(){
    let html="";
    tickerData.forEach(d=>{
        let color = d.change>=0?"#00C076":"#F6465D";
        let arrow = d.change>=0?"▲":"▼";

        html += `<span class="ticker-item">
        ${d.name} ${d.price} 
        <span style="color:${color}">
        ${arrow} ${d.change}
        </span>
        </span>`;
    });

    document.getElementById("tickerData").innerHTML = html+html;
}

loadTicker();

// 🔥 LIVE UPDATE
setInterval(()=>{
    tickerData.forEach(d=>{
        let move=(Math.random()*20-10);
        d.price+=move;
        d.change=move;
    });
    loadTicker();
},3000);

// 🔥 CHART
const chart = LightweightCharts.createChart(document.getElementById('chart'),{
    layout:{background:{color:'#0B0E11'},textColor:'#fff'}
});

const candle = chart.addCandlestickSeries();

candle.setData([
 {time:'2024-01-01',open:100,high:110,low:90,close:105},
 {time:'2024-01-02',open:105,high:115,low:100,close:110},
]);

</script>

</body>
</html>
