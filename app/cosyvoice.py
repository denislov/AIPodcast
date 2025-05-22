import os
import sys
import time
 
import torch
import torchaudio
from tqdm import tqdm
 
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav

# 将第三方库Matcha-TTS的路径添加到系统路径中
sys.path.append('third_party/Matcha-TTS')
 
# 记录开始时间
start = time.time()
# 初始化CosyVoice2模型，指定预训练模型路径，不加载jit和trt模型，使用fp32
cosyvoice = CosyVoice2('pretrained_models/CosyVoice2-0.5B',
                       load_jit=False, load_trt=False, fp16=False)
# 设置最大音量
max_val = 0.8
# 设置说话人名称
speaker = '穗'
# 设置说话人信息文件的路径
spk2info_path = f'pretrained_models/CosyVoice2-0.5B/spk2info.pt'
# 设置提示文本
prompt_text = "我知道，那件事之后，良爷可能觉得有些事都是老天定的，人怎么做都没用，但我觉得不是这样的。"
# 设置要合成的文本列表
tts_text_list = ["收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。",
                 "人类不断挑战极限，在这一过程中超越自我，攀登新的高度。登山作为一项古老的极限运动，自古以来就吸引了无数冒险者，即使在现代，依然是许多人的热爱。"]
 
# 加载16kHz的提示语音
prompt_speech_16k = load_wav(f'{speaker}.wav', 16000)
 
# 如果说话人信息文件存在，则加载
if os.path.exists(spk2info_path):
    spk2info = torch.load(
        spk2info_path, map_location=cosyvoice.frontend.device)
else:
    spk2info = {}
 
# 想要重新生成当前说话人音频特征的取消以下注释
#if speaker in spk2info:
#    del spk2info[speaker]
 
if speaker not in spk2info:
    # 获取音色embedding
    embedding = cosyvoice.frontend._extract_spk_embedding(prompt_speech_16k)
    # 获取语音特征
    prompt_speech_resample = torchaudio.transforms.Resample(orig_freq=16000, new_freq=cosyvoice.sample_rate)(prompt_speech_16k)
    speech_feat, speech_feat_len = cosyvoice.frontend._extract_speech_feat(prompt_speech_resample)
    # 获取语音token
    speech_token, speech_token_len = cosyvoice.frontend._extract_speech_token(prompt_speech_16k)
    # 将音色embedding、语音特征和语音token保存到字典中
    spk2info[speaker] = {'embedding': embedding,
                         'speech_feat': speech_feat, 'speech_token': speech_token}
    # 保存音色embedding
    torch.save(spk2info, spk2info_path)
print('Load time:', time.time()-start)
 
 
# 定义一个文本到语音的函数，参数包括文本内容、是否流式处理、语速和是否使用文本前端处理
def tts_sft(tts_text, speaker_info:dict,stream=False, speed=1.0, text_frontend=True):
    '''
    参数：
        tts_text：要合成的文本
        speaker：说话人音频特征
        stream：是否流式处理
        speed：语速
        text_frontend：是否使用文本前端处理
    返回值：
        合成后的音频
    '''
    # 使用tqdm库来显示进度条，对文本进行标准化处理并分割
    for i in tqdm(cosyvoice.frontend.text_normalize(tts_text, split=True, text_frontend=text_frontend)):
        # 提取文本的token和长度
        tts_text_token, tts_text_token_len = cosyvoice.frontend._extract_text_token(i)
        # 提取提示文本的token和长度
        prompt_text_token, prompt_text_token_len = cosyvoice.frontend._extract_text_token(prompt_text)
        # 获取说话人的语音token长度，并转换为torch张量，移动到指定设备
        speech_token_len = torch.tensor([speaker_info['speech_token'].shape[1]], dtype=torch.int32).to(cosyvoice.frontend.device)
        # 获取说话人的语音特征长度，并转换为torch张量，移动到指定设备
        speech_feat_len = torch.tensor([speaker_info['speech_feat'].shape[1]], dtype=torch.int32).to(cosyvoice.frontend.device)
        # 构建模型输入字典，包括文本、文本长度、提示文本、提示文本长度、LLM提示语音token、LLM提示语音token长度、流提示语音token、流提示语音token长度、提示语音特征、提示语音特征长度、LLM嵌入和流嵌入
        model_input = {'text': tts_text_token, 'text_len': tts_text_token_len,
                       'prompt_text': prompt_text_token, 'prompt_text_len': prompt_text_token_len,
                       'llm_prompt_speech_token': speaker_info['speech_token'], 'llm_prompt_speech_token_len': speech_token_len,
                       'flow_prompt_speech_token':speaker_info['speech_token'], 'flow_prompt_speech_token_len': speech_token_len,
                       'prompt_speech_feat': speaker_info['speech_feat'], 'prompt_speech_feat_len': speech_feat_len,
                       'llm_embedding': speaker_info['embedding'], 'flow_embedding': speaker_info['embedding']}
        # 使用模型进行文本到语音的转换，并迭代输出结果
        for model_output in cosyvoice.model.tts(**model_input, stream=stream, speed=speed):
            yield model_output
 
 
# 遍历文本列表
for text in tts_text_list:
    # 记录开始时间
    start = time.time()
    # 遍历每个文本的生成结果
    for i, j in enumerate(tts_sft(text, speaker=spk2info['穗'],stream=False, speed=1.0, text_frontend=True)):
        # 保存生成的语音到文件，文件名包含文本的前四个字符
        torchaudio.save('穗_{}.wav'.format(
            text[0:4]), j['tts_speech'], cosyvoice.sample_rate)
    # 打印处理时间
    print('time:', time.time()-start)