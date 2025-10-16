# coding: utf-8
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

from openai import OpenAI

# 初始化 DeepSeek 客户端
client = OpenAI(api_key="", base_url="https://api.deepseek.com")


@csrf_exempt
def chat(request):
    if request.method in ['GET', 'POST']:
        # 获取用户输入
        if request.method == 'POST':
            user_input = request.POST.get('question')
        else:  # GET 请求
            user_input = request.GET.get('question')

        if not user_input:
            return JsonResponse({'error': 'No question provided'}, status=400)

        # 从 session 中获取对话历史，如果不存在则初始化
        text = request.session.get('text', [
            {"role": "system", "content": "你是一个代码学习助手，专注于分步骤回答用户的问题。不要在回答中重复自我介绍。"}
        ])

        # 添加用户输入到对话历史
        text.append({"role": "user", "content": user_input})

        # 确保对话历史不超过 8000 字符
        while sum(len(content["content"]) for content in text) > 8000:
            del text[0]

        # 保存更新后的对话历史到 session
        request.session['text'] = text

        # 使用 DeepSeek API 进行流式对话
        def generate():
            response_stream = client.chat.completions.create(
                model="deepseek-coder",
                messages=text,
                stream=True  # 启用流式传输
            )

            assistant_response = ""
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_response += content
                    yield f"data: {json.dumps({'response': content})}\n\n"

            # 过滤掉重复的系统提示内容
            if "你是一个代码学习助手，专注于分步骤回答用户的问题。" in assistant_response:
                assistant_response = assistant_response.replace("你是一个代码学习助手，专注于分步骤回答用户的问题。", "").strip()

            # 将助手回复添加到对话历史
            text.append({"role": "assistant", "content": assistant_response})
            request.session['text'] = text

        # 返回流式响应
        return StreamingHttpResponse(generate(), content_type='text/event-stream')

    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def clear_chat(request):
    if request.method == 'POST':
        if 'text' in request.session:
            del request.session['text']
            request.session.modified = True
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
