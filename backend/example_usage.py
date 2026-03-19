"""
音乐源使用示例
展示如何切换和使用不同的音乐源
"""

from sources import SourceFactory


def example_spotify():
    """Spotify 音乐源示例"""
    print("\n" + "="*60)
    print("📌 Spotify 音乐源示例")
    print("="*60)
    
    try:
        # 创建 Spotify 源
        spotify = SourceFactory.create('spotify', {
            'client_id': 'YOUR_CLIENT_ID',  # 替换为你的 Client ID
            'client_secret': 'YOUR_CLIENT_SECRET'  # 替换为你的 Client Secret
        })
        
        # 认证
        if spotify.authenticate():
            print("\n✓ Spotify 认证成功\n")
            
            # 搜索音乐
            query = "Imagine John Lennon"
            print(f"🔍 搜索: {query}")
            results = spotify.search(query, limit=5)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['title']} - {result['artist']}")
                print(f"   ID: {result['id']}")
                print(f"   Duration: {result['duration']}ms")
                print(f"   Preview: {result.get('preview_url', 'N/A')}")
            
            # 下载第一个结果
            if results:
                first_music = results[0]
                print(f"\n📥 下载: {first_music['title']}")
                save_path = f"/tmp/spotify_{first_music['id']}.mp3"
                spotify.get_audio_file(first_music['id'], save_path)
        else:
            print("✗ Spotify 认证失败")
    
    except Exception as e:
        print(f"错误: {e}")


def example_local_file():
    """本地文件音乐源示例"""
    print("\n" + "="*60)
    print("📌 本地文件音乐源示例")
    print("="*60)
    
    try:
        # 创建本地文件源
        local = SourceFactory.create('local_file', {
            'music_dir': os.path.expanduser('~/Music'),
            'recursive': True
        })
        
        print(f"\n✓ 本地文件源已就绪")
        print(f"音乐文件夹: {local.music_dir}\n")
        
        # 搜索音乐
        query = "love"  # 搜索文件名包含 "love" 的音乐
        print(f"🔍 搜索: {query}")
        results = local.search(query, limit=5)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   格式: {result['format']}")
            print(f"   路径: {result['path']}")
        
        # 列出所有音乐
        print(f"\n📋 所有本地音乐:")
        all_music = local.list_available_music()
        print(f"   共找到 {len(all_music)} 首音乐")
        
        for music in all_music[:5]:  # 显示前 5 首
            print(f"   - {music['title']} ({music['format']})")
        
        if len(all_music) > 5:
            print(f"   ... 及其他 {len(all_music) - 5} 首")
    
    except Exception as e:
        print(f"错误: {e}")


def example_source_factory():
    """SourceFactory 使用示例"""
    print("\n" + "="*60)
    print("📌 SourceFactory 使用示例")
    print("="*60)
    
    # 列出所有可用源
    print("\n✓ 可用的音乐源:")
    sources = SourceFactory.get_available_sources()
    for source in sources:
        print(f"   - {source}")
    
    # 切换源
    print("\n✓ 切换到本地文件源...")
    local_source = SourceFactory.set_current('local_file', {
        'music_dir': os.path.expanduser('~/Music')
    })
    
    # 获取当前源
    current = SourceFactory.get_current()
    print(f"   当前源: {current}")
    
    # 切换源
    print("\n✓ 切换到 Spotify 源...")
    spotify_source = SourceFactory.set_current('spotify', {
        'client_id': 'demo',
        'client_secret': 'demo'
    })
    
    current = SourceFactory.get_current()
    print(f"   当前源: {current}")


if __name__ == '__main__':
    import os
    
    print("\n🎵 音乐扒谱应用 - 音乐源示例\n")
    
    # 运行示例
    example_source_factory()
    print("\n" + "-"*60)
    example_local_file()
    print("\n" + "-"*60)
    # example_spotify()  # 需要真实的 Spotify 凭证
    
    print("\n" + "="*60)
    print("✓ 示例完成")
    print("="*60 + "\n")
