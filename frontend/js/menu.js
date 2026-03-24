// 菜单配置
const menuItems = [
    { path: '/', label: '首页', icon: '🏠' },
    { path: '/capture', label: '录音采集', icon: '🎙️' },
    { path: '/songs', label: '歌曲库', icon: '🎵' },
    { path: '/artists', label: '歌手', icon: '👤' },
    { path: '/transcribe', label: '提取', icon: '🎼' }
];

// 获取当前路径
let currentPath = window.location.pathname;
if (currentPath === '/index.html') currentPath = '/';

// 判断是否为首页
const isHome = currentPath === '/';

// 生成菜单 HTML
const sidebarHTML = `
<style>
.sidebar{position:fixed;left:0;top:0;width:200px;height:100vh;background:#1a1a2e;color:#fff;padding:20px 0;z-index:9999}
.nav-item{padding:15px 20px;cursor:pointer;color:#aaa}
.nav-item:hover,.nav-item.active{background:rgba(78,205,196,0.2);color:#4ecdc4}
</style>
<div class="sidebar">
    <h2 style="padding:0 20px 20px;border-bottom:1px solid rgba(255,255,255,0.1);color:#4ecdc4;margin:0">音乐扒谱</h2>
    ${menuItems.map(item => {
        let active = false;
        if (isHome && item.path === '/') active = true;
        else if (!isHome && currentPath.startsWith(item.path)) active = true;
        return `<div class="nav-item ${active ? 'active' : ''}" onclick="location.href='${item.path}'">${item.icon} ${item.label}</div>`;
    }).join('')}
</div>
`;

// 注入侧边栏
document.body.insertAdjacentHTML = document.body.insertAdjacentHTML || function() {};
document.body.insertAdjacentHTML('afterbegin', sidebarHTML);

// 给 body 添加左边距
document.body.style.marginLeft = '200px';
document.body.style.minHeight = '100vh';
