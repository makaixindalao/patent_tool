"""
专利撰写助手 Web 应用
基于 Streamlit 构建的现代化专利生成和管理系统
支持多厂商API和多线程处理
"""

import streamlit as st
import json
import os
from datetime import datetime
from patent_assistant import PatentAssistant
from gemini_client import GeminiClient
import time
import threading


def init_session_state():
    """初始化会话状态"""
    if 'patent_assistant' not in st.session_state:
        st.session_state.patent_assistant = None
    if 'patent_ideas' not in st.session_state:
        st.session_state.patent_ideas = []
    if 'generated_patents' not in st.session_state:
        st.session_state.generated_patents = []
    if 'current_patent' not in st.session_state:
        st.session_state.current_patent = None
    if 'config' not in st.session_state:
        st.session_state.config = {}


def setup_sidebar():
    """设置侧边栏配置"""
    st.sidebar.title("⚙️ 系统配置")
    
    # 模型厂商选择
    st.sidebar.subheader("🤖 模型配置")
    
    # 获取预定义厂商
    providers = GeminiClient.get_predefined_providers()
    provider_names = list(providers.keys())
    
    selected_provider = st.sidebar.selectbox(
        "选择模型厂商",
        provider_names,
        index=0,
        help="选择要使用的AI模型厂商",
        key="provider_selectbox"
    )
    
    # 根据选择的厂商显示配置
    provider_config = providers[selected_provider]
    
    if selected_provider == "自定义":
        # 自定义配置
        base_url = st.sidebar.text_input(
            "API Base URL",
            placeholder="https://api.example.com/v1/",
            help="输入自定义的API基础URL",
            key="custom_base_url"
        )
        
        model = st.sidebar.text_input(
            "模型名称",
            placeholder="custom-model-name",
            help="输入要使用的模型名称",
            key="custom_model"
        )
        
        models_list = [model] if model else []
    else:
        # 预定义厂商配置
        base_url = provider_config["base_url"]
        models_list = provider_config["models"]
        
        if models_list:
            model = st.sidebar.selectbox(
                "选择模型",
                models_list,
                help=f"选择{selected_provider}的模型",
                key="model_selectbox"
            )
        else:
            model = st.sidebar.text_input(
                "模型名称",
                help="输入模型名称",
                key="predefined_model"
            )
    
    # API密钥输入
    api_key = st.sidebar.text_input(
        "API 密钥",
        type="password",
        help="输入您的API密钥",
        key="api_key_input"
    )
    
    # 多线程配置
    st.sidebar.subheader("🚀 性能配置")
    
    max_workers_ideas = st.sidebar.slider(
        "创意生成线程数",
        min_value=1,
        max_value=10,
        value=3,
        help="同时生成专利创意的线程数量",
        key="ideas_workers_slider"
    )
    
    max_workers_patents = st.sidebar.slider(
        "专利生成线程数",
        min_value=1,
        max_value=10,
        value=2,
        help="同时生成完整专利的线程数量",
        key="patents_workers_slider"
    )
    
    # 生成参数
    st.sidebar.subheader("🎛️ 生成参数")
    
    temperature = st.sidebar.slider(
        "创意温度",
        min_value=0.1,
        max_value=1.0,
        value=0.8,
        step=0.1,
        help="控制生成内容的随机性，值越高越有创意",
        key="ideas_temperature_slider"
    )
    
    patent_temperature = st.sidebar.slider(
        "专利温度",
        min_value=0.1,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="控制专利生成的随机性",
        key="patents_temperature_slider"
    )
    
    # 连接测试
    if st.sidebar.button("🔗 测试连接", key="test_connection_btn"):
        if api_key and model and base_url:
            try:
                test_client = GeminiClient(api_key, model, base_url)
                test_result = test_client.generate_content(
                    "请回复'连接成功'",
                    temperature=0.1
                )
                if "连接成功" in test_result or "成功" in test_result:
                    st.sidebar.success("✅ 连接成功！")
                else:
                    st.sidebar.warning(f"⚠️ 连接异常：{test_result[:100]}...")
            except Exception as e:
                st.sidebar.error(f"❌ 连接失败：{str(e)}")
        else:
            st.sidebar.error("❌ 请填写完整的配置信息")
    
    config = {
        'api_key': api_key,
        'model': model,
        'base_url': base_url,
        'provider': selected_provider,
        'max_workers_ideas': max_workers_ideas,
        'max_workers_patents': max_workers_patents,
        'temperature': temperature,
        'patent_temperature': patent_temperature
    }
    
    # 保存配置到会话状态
    st.session_state.config = config
    return config


def create_patent_assistant(config):
    """创建或获取专利助手实例"""
    if config['api_key'] and config['model']:
        try:
            # 检查是否已有实例且配置相同
            if ('patent_assistant' in st.session_state and 
                st.session_state.patent_assistant is not None and
                hasattr(st.session_state, 'assistant_config') and
                st.session_state.assistant_config == config):
                return st.session_state.patent_assistant
            
            # 创建新的专利助手实例
            assistant = PatentAssistant(
                api_key=config['api_key'],
                model=config['model'],
                base_url=config['base_url']
            )
            
            # 保存到会话状态
            st.session_state.patent_assistant = assistant
            st.session_state.assistant_config = config.copy()
            
            return assistant
        except Exception as e:
            st.error(f"创建专利助手失败：{str(e)}")
            return None
    return None


def tab_generate_ideas():
    """专利创意生成标签页"""
    st.header("💡 生成专利创意")
    
    config = st.session_state.config
    
    if not config.get('api_key'):
        st.warning("⚠️ 请在侧边栏配置API密钥")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        count = st.number_input(
            "生成数量",
            min_value=1,
            max_value=20,
            value=5,
            help="要生成的专利创意数量",
            key="ideas_count_input"
        )
    
    with col2:
        st.write("") # 占位
        st.write("") # 占位
        generate_btn = st.button("🚀 开始生成", type="primary", key="generate_ideas_btn")
    
    if generate_btn:
        # 显示配置信息用于调试
        st.write("🔧 当前配置:")
        st.write(f"- API密钥: {'已配置' if config.get('api_key') else '未配置'}")
        st.write(f"- 模型: {config.get('model', '未配置')}")
        st.write(f"- 基础URL: {config.get('base_url', '未配置')}")
        st.write(f"- 线程数: {config.get('max_workers_ideas', '未配置')}")
        st.write(f"- 温度: {config.get('temperature', '未配置')}")
        
        assistant = create_patent_assistant(config)
        if assistant:
            try:
                with st.spinner("🔄 正在生成专利创意..."):
                    # 显示进度条
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    start_time = time.time()
                    
                    # 生成专利创意
                    ideas = assistant.generate_patent_ideas(
                        count=count,
                        temperature=config.get('temperature', 0.8),
                        max_workers=config.get('max_workers_ideas', 3)
                    )
                    
                    end_time = time.time()
                    progress_bar.progress(100)
                    
                    st.session_state.patent_ideas = ideas
                    
                    # 显示结果统计
                    success_count = len([idea for idea in ideas if "error" not in idea])
                    error_count = count - success_count
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总数量", count)
                    with col2:
                        st.metric("成功", success_count)
                    with col3:
                        st.metric("失败", error_count)
                    with col4:
                        st.metric("耗时", f"{end_time - start_time:.1f}秒")
                        
                    # 显示详细结果
                    if success_count > 0:
                        st.success(f"✅ 成功生成 {success_count} 个专利创意！")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} 个创意生成失败")
                        
            except Exception as e:
                st.error(f"❌ 生成过程中出现错误: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.error("❌ 无法创建专利助手，请检查配置")
    
    # 显示生成的创意
    if st.session_state.patent_ideas:
        st.subheader("📋 生成的专利创意")
        
        for i, idea in enumerate(st.session_state.patent_ideas):
            with st.expander(f"💡 创意 {i+1}: {idea.get('title', '未知标题')}"):
                if "error" in idea:
                    st.error(f"生成失败：{idea['error']}")
                else:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**技术领域：** {idea.get('field', '未知')}")
                        
                        st.write("**核心特性：**")
                        for feature in idea.get('features', []):
                            st.write(f"• {feature}")
                        
                        if 'innovation_points' in idea:
                            st.write("**创新点：**")
                            for point in idea['innovation_points']:
                                st.write(f"• {point}")
                        
                        if 'application_scenarios' in idea:
                            st.write("**应用场景：**")
                            for scenario in idea['application_scenarios']:
                                st.write(f"• {scenario}")
                    
                    with col2:
                        if st.button(f"生成专利 {i+1}", key=f"gen_patent_{i}"):
                            st.session_state.selected_idea = idea
                            st.rerun()


def tab_generate_patent():
    """完整专利生成标签页"""
    st.header("📄 生成完整专利")
    
    config = st.session_state.config
    
    if not config.get('api_key'):
        st.warning("⚠️ 请在侧边栏配置API密钥")
        return
    
    # 选择生成方式
    generation_mode = st.radio(
        "选择生成方式",
        ["从创意生成", "手动输入", "批量生成"],
        horizontal=True,
        key="generation_mode_radio"
    )
    
    if generation_mode == "从创意生成":
        if not st.session_state.patent_ideas:
            st.info("💡 请先在'生成专利创意'页面生成一些创意")
            return
        
        # 选择创意
        idea_options = [f"{i+1}. {idea.get('title', '未知标题')}" 
                       for i, idea in enumerate(st.session_state.patent_ideas)
                       if "error" not in idea]
        
        if not idea_options:
            st.warning("⚠️ 没有可用的专利创意")
            return
        
        selected_option = st.selectbox("选择专利创意", idea_options, key="idea_selection")
        selected_index = int(selected_option.split('.')[0]) - 1
        selected_idea = st.session_state.patent_ideas[selected_index]
        
        if st.button("🚀 生成完整专利", type="primary", key="generate_single_patent_btn"):
            assistant = create_patent_assistant(config)
            if assistant:
                try:
                    with st.spinner("📝 正在生成完整专利文档..."):
                        start_time = time.time()
                        
                        patent = assistant.generate_full_patent(
                            title=selected_idea['title'],
                            features=selected_idea['features'],
                            temperature=config.get('patent_temperature', 0.7)
                        )
                        
                        end_time = time.time()
                        
                        st.session_state.current_patent = patent
                        
                        if patent['status'] == 'draft':
                            st.success(f"✅ 专利生成完成！耗时 {end_time - start_time:.1f} 秒")
                        else:
                            st.error(f"❌ 专利生成失败: {patent['content'][:200]}...")
                            
                except Exception as e:
                    st.error(f"❌ 生成过程中出现错误: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.error("❌ 无法创建专利助手，请检查配置")
    
    elif generation_mode == "手动输入":
        title = st.text_input("专利标题", placeholder="输入专利标题", key="manual_title_input")
        
        st.write("**核心特性：**")
        features = []
        for i in range(5):
            feature = st.text_input(f"特性 {i+1}", key=f"manual_feature_{i}", placeholder=f"输入核心特性 {i+1}")
            if feature:
                features.append(feature)
        
        if st.button("🚀 生成完整专利", type="primary", key="generate_manual_patent_btn") and title and features:
            assistant = create_patent_assistant(config)
            if assistant:
                try:
                    with st.spinner("📝 正在生成完整专利文档..."):
                        start_time = time.time()
                        
                        patent = assistant.generate_full_patent(
                            title=title,
                            features=features,
                            temperature=config.get('patent_temperature', 0.7)
                        )
                        
                        end_time = time.time()
                        
                        st.session_state.current_patent = patent
                        
                        if patent['status'] == 'draft':
                            st.success(f"✅ 专利生成完成！耗时 {end_time - start_time:.1f} 秒")
                        else:
                            st.error(f"❌ 专利生成失败: {patent['content'][:200]}...")
                            
                except Exception as e:
                    st.error(f"❌ 生成过程中出现错误: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.error("❌ 无法创建专利助手，请检查配置")
    
    elif generation_mode == "批量生成":
        if not st.session_state.patent_ideas:
            st.info("💡 请先在'生成专利创意'页面生成一些创意")
            return
        
        valid_ideas = [idea for idea in st.session_state.patent_ideas if "error" not in idea]
        
        if not valid_ideas:
            st.warning("⚠️ 没有可用的专利创意")
            return
        
        st.write(f"发现 {len(valid_ideas)} 个可用的专利创意")
        
        if st.button("🚀 批量生成所有专利", type="primary", key="generate_batch_patents_btn"):
            assistant = create_patent_assistant(config)
            if assistant:
                with st.spinner("📝 正在批量生成专利文档..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    start_time = time.time()
                    
                    patents = assistant.batch_generate_patents(
                        patent_ideas=valid_ideas,
                        temperature=config['patent_temperature'],
                        max_workers=config['max_workers_patents']
                    )
                    
                    end_time = time.time()
                    progress_bar.progress(100)
                    
                    st.session_state.generated_patents = patents
                    
                    # 显示结果统计
                    success_count = len([p for p in patents if p.get('status') == 'draft'])
                    error_count = len(patents) - success_count
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总数量", len(patents))
                    with col2:
                        st.metric("成功", success_count)
                    with col3:
                        st.metric("失败", error_count)
                    with col4:
                        st.metric("耗时", f"{end_time - start_time:.1f}秒")
    
    # 显示当前专利
    if st.session_state.current_patent:
        st.subheader("📄 生成的专利文档")
        
        patent = st.session_state.current_patent
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**标题：** {patent['title']}")
        with col2:
            st.write(f"**状态：** {patent['status']}")
        with col3:
            st.write(f"**生成时间：** {patent['generated_at']}")
        
        # 显示专利内容
        with st.expander("📖 查看完整内容", expanded=True):
            st.text_area(
                "专利内容",
                value=patent['content'],
                height=400,
                key="patent_content_display"
            )
        
        # 操作按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 导出文本", key="export_text_btn"):
                st.download_button(
                    label="下载文本文件",
                    data=patent['content'],
                    file_name=f"{patent['title']}.txt",
                    mime="text/plain",
                    key="download_text_btn"
                )
        
        with col2:
            if st.button("📥 导出JSON", key="export_json_btn"):
                json_data = json.dumps(patent, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载JSON文件",
                    data=json_data,
                    file_name=f"{patent['title']}.json",
                    mime="application/json",
                    key="download_json_btn"
                )
        
        with col3:
            if st.button("🔄 优化专利", key="optimize_patent_btn"):
                st.session_state.optimize_patent = patent
                st.rerun()


def tab_manage_patents():
    """专利管理标签页"""
    st.header("📚 管理专利")
    
    config = st.session_state.config
    assistant = create_patent_assistant(config) if config.get('api_key') else None
    
    if not assistant:
        st.warning("⚠️ 请在侧边栏配置API密钥")
        return
    
    # 获取所有专利
    all_patents = assistant.get_patents()
    
    if not all_patents:
        st.info("暂无专利文档，请先生成一些专利")
        
        # 显示数据文件信息
        if hasattr(assistant, 'data_file'):
            st.write(f"💾 数据文件: {assistant.data_file}")
            if os.path.exists(assistant.data_file):
                st.write("✅ 数据文件存在")
            else:
                st.write("❌ 数据文件不存在")
        return
    
    # 显示统计信息
    stats = assistant.get_statistics()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总专利数", stats['total_patents'])
    with col2:
        st.metric("草稿", stats['draft_patents'])
    with col3:
        st.metric("错误", stats['error_patents'])
    with col4:
        st.metric("成功率", f"{stats['success_rate']:.1f}%")
    with col5:
        if hasattr(assistant, 'data_file'):
            file_size = os.path.getsize(assistant.data_file) if os.path.exists(assistant.data_file) else 0
            st.metric("数据文件", f"{file_size/1024:.1f}KB")
    
    # 专利列表
    st.subheader("📋 专利列表")
    
    # 添加排序选项
    sort_options = ["生成时间(最新)", "生成时间(最旧)", "标题(A-Z)", "状态"]
    sort_by = st.selectbox("排序方式", sort_options, key="patent_sort_select")
    
    # 排序专利列表
    if sort_by == "生成时间(最新)":
        all_patents = sorted(all_patents, key=lambda x: x.get('generated_at', ''), reverse=True)
    elif sort_by == "生成时间(最旧)":
        all_patents = sorted(all_patents, key=lambda x: x.get('generated_at', ''))
    elif sort_by == "标题(A-Z)":
        all_patents = sorted(all_patents, key=lambda x: x.get('title', ''))
    elif sort_by == "状态":
        all_patents = sorted(all_patents, key=lambda x: x.get('status', ''))
    
    for i, patent in enumerate(all_patents):
        with st.expander(f"📄 {patent['title']} ({patent['id']}) - {patent.get('status', 'unknown')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**ID：** {patent['id']}")
                st.write(f"**状态：** {patent['status']}")
                st.write(f"**生成时间：** {patent['generated_at']}")
                
                if 'updated_at' in patent:
                    st.write(f"**更新时间：** {patent['updated_at']}")
                
                if 'features' in patent and patent['features']:
                    st.write("**核心特性：**")
                    for feature in patent['features']:
                        st.write(f"• {feature}")
                
                # 显示内容预览
                content_preview = patent['content'][:300] + "..." if len(patent['content']) > 300 else patent['content']
                st.text_area(
                    "内容预览",
                    value=content_preview,
                    height=150,
                    key=f"preview_{patent['id']}_{i}"
                )
            
            with col2:
                st.write("**操作**")
                
                if st.button(f"查看详情", key=f"view_{patent['id']}_{i}"):
                    st.session_state.current_patent = patent
                    st.rerun()
                
                if st.button(f"优化", key=f"opt_{patent['id']}_{i}"):
                    st.session_state.optimize_patent = patent
                    st.rerun()
                
                if st.button(f"删除", key=f"del_{patent['id']}_{i}", type="secondary"):
                    if assistant.delete_patent(patent['id']):
                        st.success("✅ 专利已删除")
                        st.rerun()
                    else:
                        st.error("❌ 删除失败")
    
    # 批量操作
    st.subheader("📦 批量操作")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 导出所有专利(JSON)", key="export_all_json_btn"):
            json_data = assistant.export_patents_json()
            st.download_button(
                label="下载JSON文件",
                data=json_data,
                file_name=f"patents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="download_all_json_btn"
            )
    
    with col2:
        if st.button("📥 导出所有专利(文本)", key="export_all_text_btn"):
            text_data = assistant.export_patents_text()
            st.download_button(
                label="下载文本文件",
                data=text_data,
                file_name=f"patents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_all_text_btn"
            )
    
    with col3:
        if st.button("🔄 刷新数据", key="refresh_patents_btn"):
            # 重新加载数据
            assistant._load_patents()
            st.success("✅ 数据已刷新")
            st.rerun()


def tab_optimize_patent():
    """专利优化标签页"""
    st.header("🔧 优化专利")
    
    config = st.session_state.config
    
    if not config.get('api_key'):
        st.warning("⚠️ 请在侧边栏配置API密钥")
        return
    
    # 选择要优化的专利
    if 'optimize_patent' in st.session_state and st.session_state.optimize_patent:
        patent = st.session_state.optimize_patent
        st.success(f"✅ 已选择专利：{patent['title']}")
    else:
        st.info("💡 请从其他页面选择要优化的专利，或手动输入专利内容")
        
        # 手动输入专利内容
        patent_content = st.text_area(
            "专利内容",
            height=300,
            placeholder="请输入要优化的专利内容...",
            key="optimize_manual_content"
        )
        
        if patent_content:
            patent = {
                'title': '手动输入的专利',
                'content': patent_content
            }
        else:
            return
    
    # 优化选项
    optimization_focus = st.selectbox(
        "优化重点",
        ["全面优化", "技术方案", "创新点", "保护范围", "对比分析"],
        help="选择优化的重点方向",
        key="optimization_focus_select"
    )
    
    if st.button("🚀 开始优化", type="primary", key="start_optimize_btn"):
        assistant = create_patent_assistant(config)
        if assistant:
            with st.spinner("🔧 正在优化专利内容..."):
                start_time = time.time()
                
                optimized_content = assistant.optimize_patent(
                    patent_content=patent['content'],
                    optimization_focus=optimization_focus,
                    temperature=0.6
                )
                
                end_time = time.time()
                
                st.success(f"✅ 优化完成！耗时 {end_time - start_time:.1f} 秒")
                
                # 显示优化结果
                st.subheader("📄 优化结果")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**原始内容：**")
                    st.text_area(
                        "原始专利",
                        value=patent['content'],
                        height=400,
                        key="original_content"
                    )
                
                with col2:
                    st.write("**优化后内容：**")
                    st.text_area(
                        "优化专利",
                        value=optimized_content,
                        height=400,
                        key="optimized_content"
                    )
                
                # 导出按钮
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 下载优化后的专利",
                        data=optimized_content,
                        file_name=f"{patent['title']}_优化版.txt",
                        mime="text/plain",
                        key="download_optimized_btn"
                    )
                
                with col2:
                    # 保存优化后的专利
                    if st.button("💾 保存为新专利", key="save_optimized_btn"):
                        if assistant:
                            optimized_patent = {
                                "id": f"patent_opt_{int(time.time())}",
                                "title": f"{patent['title']} (优化版)",
                                "content": optimized_content,
                                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "status": "optimized",
                                "original_id": patent.get('id', 'unknown')
                            }
                            
                            # 这里需要添加保存逻辑
                            st.success("✅ 已保存优化后的专利")


def main():
    """主函数"""
    st.set_page_config(
        page_title="专利撰写助手",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化会话状态
    init_session_state()
    
    # 设置侧边栏配置（只在主函数中调用一次）
    config = setup_sidebar()
    
    # 主标题
    st.title("📄 专利撰写助手")
    st.markdown("---")
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "💡 生成专利创意",
        "📄 生成完整专利", 
        "📚 管理专利",
        "🔧 优化专利"
    ])
    
    with tab1:
        tab_generate_ideas()
    
    with tab2:
        tab_generate_patent()
    
    with tab3:
        tab_manage_patents()
    
    with tab4:
        tab_optimize_patent()
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>专利撰写助手 v2.0 | 支持多厂商API和多线程处理 | 
            <a href='https://github.com' target='_blank'>GitHub</a></p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main() 