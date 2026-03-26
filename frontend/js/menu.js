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
            { path: '/audio-sources/list', label: '音源列表' }
        ]
    }
];

// 获取当前路径
let currentPath = window.location.pathname;
if (currentPath === '/index.html') currentPath = '/';

// 获取页面原有内容
let originalContent = document.body.innerHTML;

// 生成菜单HTML
let html = `
<style>
body{margin:0;min-height:100vh}
.sidebar{position:fixed;left:0;top:0;width:200px;height:100vh;background:#1a1a2e;color:#fff;padding:20px 0;z-index:9999;box-sizing:border-box}
.logo{padding:0 20px 20px;border-bottom:1px solid rgba(255,255,255,0.1)}
.logo h1{font-size:18px;color:#4ecdc4;margin:0}
.nav-item{padding:12px 20px;cursor:pointer;color:#aaa;display:flex;align-items:center;gap:8px}
.nav-item:hover,.nav-item.active{background:rgba(78,205,196,0.2);color:#4ecdc4}
.submenu{display:none;padding-left:0}
.submenu.open{display:block}
.submenu-item{padding:10px 20px;cursor:pointer;color:#888;font-size:14px}
.submenu-item:hover,.submenu-item.active{color:#4ecdc4}
.arrow{margin-left:auto;font-size:10px}
.main-content{margin-left:200px;padding:20px;min-height:100vh}
</style>
<div class="sidebar">
    <div class="logo"><h1>🎵 音乐扒谱</h1></div>
`;

menuItems.forEach(item => {
    let isParentActive = currentPath === item.path || (item.path !== '/' && currentPath.startsWith(item.path));
    
    if (item.submenu) {
        html += '<div class="nav-item" onclick="this.classList.toggle(\'active\');this.nextElementSibling.classList.toggle(\'open\')">';
        html += item.icon + ' ' + item.label + ' <span class="arrow">▼</span></div>';
        html += '<div class="submenu ' + (isParentActive ? 'open' : '') + '">';
        item.submenu.forEach(sub => {
            let isActive = currentPath === sub.path;
            html += '<div class="submenu-item ' + (isActive ? 'active' : '') + '" onclick="location.href=\'' + sub.path + '\'">' + sub.label + '</div>';
        });
        html += '</div>';
    } else {
        let isActive = (item.path === '/' && currentPath === '/') || currentPath.startsWith(item.path);
        html += '<div class="nav-item ' + (isActive ? 'active' : '') + '" onclick="location.href=\'' + item.path + '\'">' + item.icon + ' ' + item.label + '</div>';
    }
});

html += '</div><div class="main-content">' + originalContent + '</div>';

// 替换页面内容
document.body.innerHTML = html;
