// 菜单配置
const menuItems = [
    { path: '/', label: '首页', icon: '🏠' },
    { 
        path: '/capture', 
        label: '录音', 
        icon: '🎙️',
        submenu: [
            { path: '/capture', label: '录音采集' },
            { path: '/recordings', label: '录音文件' }
        ]
    },
    { 
        path: '/songs', 
        label: '歌曲库', 
        icon: '🎵',
        submenu: [
            { path: '/songs', label: '查询歌曲' },
            { path: '/songs/add', label: '创建歌曲' }
        ]
    },
    { 
        path: '/artists', 
        label: '歌手', 
        icon: '👤',
        submenu: [
            { path: '/artists', label: '歌手列表' },
            { path: '/artists/add', label: '新增歌手' }
        ]
    },
    { path: '/transcribe', label: '提取', icon: '🎼' },
    { 
        path: '/audio-sources', 
        label: '音源', 
        icon: '🎧',
        submenu: [
            { path: '/audio-sources/upload', label: '上传' },
            { path: '/audio-sources', label: '音源列表' }
        ]
    }
];

// 获取当前路径
let currentPath = window.location.pathname;
if (currentPath === '/index.html') currentPath = '/';

// 生成侧边栏 HTML
let sidebarHTML = `
<style>
body{margin:0;display:flex;min-height:100vh}
.sidebar{position:fixed;left:0;top:0;width:200px;height:100vh;background:#1a1a2e;color:#fff;padding:20px 0;z-index:9999;box-sizing:border-box;overflow-y:auto}
.logo{padding:0 20px 20px;border-bottom:1px solid rgba(255,255,255,0.1)}
.logo h1{font-size:18px;color:#4ecdc4;margin:0}
.nav-item{padding:12px 20px;cursor:pointer;color:#aaa;display:flex;align-items:center;gap:8px}
.nav-item:hover,.nav-item.active{background:rgba(78,205,196,0.2);color:#4ecdc4}
.submenu{display:none;padding-left:0}
.submenu.open{display:block}
.submenu-item{padding:10px 20px 10px 40px;cursor:pointer;color:#888;font-size:14px}
.submenu-item:hover,.submenu-item.active{color:#4ecdc4}
.arrow{margin-left:auto;font-size:10px}
.main{margin-left:200px;padding:20px;flex:1}
</style>
<div class="sidebar">
    <div class="logo"><h1>🎵 音乐扒谱</h1></div>
`;

menuItems.forEach(item => {
    let isParentActive = currentPath === item.path || (item.path !== '/' && currentPath.startsWith(item.path));
    
    if (item.submenu) {
        sidebarHTML += '<div class="nav-item" onclick="this.classList.toggle(\'active\');this.nextElementSibling.classList.toggle(\'open\')">';
        sidebarHTML += item.icon + ' ' + item.label + ' <span class="arrow">▼</span></div>';
        sidebarHTML += '<div class="submenu ' + (isParentActive ? 'open' : '') + '">';
        item.submenu.forEach(sub => {
            let isActive = currentPath === sub.path;
            sidebarHTML += '<div class="submenu-item ' + (isActive ? 'active' : '') + '" onclick="location.href=\'' + sub.path + '\'">' + sub.label + '</div>';
        });
        sidebarHTML += '</div>';
    } else {
        let isActive = (item.path === '/' && currentPath === '/') || currentPath.startsWith(item.path);
        sidebarHTML += '<div class="nav-item ' + (isActive ? 'active' : '') + '" onclick="location.href=\'' + item.path + '\'">' + item.icon + ' ' + item.label + '</div>';
    }
});

sidebarHTML += '</div>';

// 等待页面加载完毕（所有内联脚本的同步代码 + 初始 DOM 操作都已完成）
// 然后：侧边栏 prepend 到 body，body 内容 wrap 进 .main
(function applyMenu() {
    // 方案：等 DOMContentLoaded + 一个小延迟，确保所有 async fetch 的首次更新已进 DOM
    // 关键：menu.js 用 defer 加载 → 在所有内联 <script> 执行完之后才运行
    // 此时 body 里已经有 "加载中..." 内容
    // 我们把 sidebar 插入到 body 最前面，body 的原始内容全部保留在 DOM 树中
    // → 页面 fetch callback 持有的 getElementById 引用依然有效，DOM 更新正常显示
    document.addEventListener('DOMContentLoaded', function() {
        // 把整个 body 内容包进 <div class="main">
        let mainDiv = document.createElement('div');
        mainDiv.className = 'main';
        while (document.body.firstChild) {
            mainDiv.appendChild(document.body.firstChild);
        }
        // 把 sidebar 和 mainDiv 都放进 body
        document.body.insertAdjacentHTML('afterbegin', sidebarHTML);
        document.body.appendChild(mainDiv);
    });
})();
