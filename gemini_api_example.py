# gemini_api_example.py
from openai import OpenAI
import os

# --- 1. 配置 API 密钥 和 OpenAI 客户端 ---
# 脚本会尝试从名为 GOOGLE_API_KEY 的环境变量中读取 API 密钥。
# 您已将其修改为直接在代码中设置。

# 全局 OpenAI 客户端实例
client = None

try:
    # 您修改为在此处直接设置 api_key
    # api_key = os.environ.get("GOOGLE_API_KEY") # 保留原始逻辑的注释供参考
    api_key = "AIzaSyBRD92F9M-WPkhwmvzuXzcjslQq3VzPxpk" # 这是您在文件中设置的占位符密钥
    if not api_key: # 检查密钥是否为空字符串
        raise ValueError("API key is not set or is empty.")
    
    # 初始化 OpenAI 客户端以兼容 Gemini
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/" # 用户提供的 base_url
    )
    print("OpenAI 客户端配置成功，指向 Gemini API (OpenAI 兼容模式)。")

except ValueError as ve:
    print(f"错误: {ve}")
    print("请确保 API 密钥已正确设置。")
    exit()
except Exception as e:
    print(f"初始化 OpenAI 客户端时发生意外错误: {e}")
    print("请检查您的 API 密钥和网络连接。")
    exit()

# --- 2. 定义调用函数 ---
def generate_content_from_gemini(prompt: str, model_name: str):
    """
    使用指定的 Gemini 模型 (通过 OpenAI 兼容接口) 生成内容。

    参数:
        prompt (str): 要发送给模型的提示。
        model_name (str): 要使用的 Gemini 模型名称。
                          用户指定的模型: "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-05-06".
                          注意：请确保此 base_url 支持这些模型名称。

    返回:
        str: 模型生成的文本，如果出错则返回错误信息。
    """
    if not client:
        return "错误: OpenAI 客户端未初始化。"
    try:
        print(f"\n正在使用 OpenAI 兼容模式调用模型: {model_name}")
        print(f"发送提示: \"{prompt}\"")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."}, # 系统提示
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model=model_name, # 使用用户指定的模型名称
            messages=messages,
            # stream=False # 默认为 False
        )

        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            finish_reason = "未知"
            if response.choices and response.choices[0].finish_reason:
                finish_reason = response.choices[0].finish_reason
            return f"模型没有返回预期的文本内容。完成原因: {finish_reason}."
            
    except Exception as e:
        return f"通过 OpenAI 兼容模式调用 Gemini API 时发生错误 ({model_name}): {e}"

# --- 3. 主程序 ---
if __name__ == "__main__":
    # 用户指定的模型
    # 默认使用 'gemini-2.5-flash-preview-05-20'
    default_model = "gemini-2.5-flash-preview-05-20"
    # 可选 'gemini-2.5-pro-preview-05-06'
    optional_pro_model = "gemini-2.5-pro-preview-05-06"

    # 您可以根据需要更改这里使用的模型
    model_to_use_for_first_example = default_model
    model_to_use_for_second_example = optional_pro_model

    print("\nGemini API Python 脚本示例 (OpenAI 兼容模式)")
    print("-------------------------------------------------")
    print(f"注意: 您指定的模型 '{default_model}' 和 '{optional_pro_model}' 是预览版本。")
    print("请确保 'https://generativelanguage.googleapis.com/v1beta/openai/' 支持这些模型名称。")
    print("如果遇到问题，请确认您有权访问这些模型。")

    # 示例 1: 使用默认的 Flash 模型
    prompt1 = "你好 Gemini, 请用一句话描述AI在未来的潜力。"
    response1 = generate_content_from_gemini(prompt1, model_to_use_for_first_example)
    print(f"\nGemini ('{model_to_use_for_first_example}' via OpenAI) 的回复:")
    print(response1)

    # 示例 2: 使用可选的 Pro 模型
    prompt2 = "请用Python语言写一个函数，计算一个列表中所有偶数的和。"
    response2 = generate_content_from_gemini(prompt2, model_to_use_for_second_example)
    print(f"\nGemini ('{model_to_use_for_second_example}' via OpenAI) 的回复:")
    print(response2)

    print("\n---")
    print("脚本执行完毕。")
    print("您可以修改脚本中的 `model_to_use_for_first_example` 和 `model_to_use_for_second_example`")
    print("变量来测试不同的模型，或者直接修改 `default_model` 和 `optional_pro_model` 的值。") 