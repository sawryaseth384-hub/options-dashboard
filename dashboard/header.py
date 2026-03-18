st.markdown(f"""
<div style="
    background: linear-gradient(90deg,#0f172a,#020617);
    padding:10px 15px;
    border-radius:10px;
    margin-bottom:10px;
">

    <div style="white-space:nowrap; overflow:hidden;">
        <div style="display:inline-block; padding-left:100%;
            animation:scroll 20s linear infinite;">
            {line1}
        </div>
    </div>

    <div style="white-space:nowrap; overflow:hidden;">
        <div style="display:inline-block; padding-left:100%;
            animation:scroll 25s linear infinite;">
            {line2}
        </div>
    </div>

</div>

<style>
@keyframes scroll {
    0% { transform: translateX(0%); }
    100% { transform: translateX(-100%); }
}
</style>
""", unsafe_allow_html=True)
