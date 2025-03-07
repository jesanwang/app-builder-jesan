# Copyright (c) 2023 Baidu, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

r"""ASR component.
"""
import uuid
import json

from appbuilder.core.component import Component
from appbuilder.core.message import Message
from appbuilder.core._exception import AppBuilderServerException
from appbuilder.core._client import HTTPClient
from appbuilder.core.components.asr.model import ShortSpeechRecognitionRequest, ShortSpeechRecognitionResponse, \
    ASRInMsg, ASROutMsg


class ASR(Component):
    r"""
    ASR组件，即对于输入的语音文件，输出语音识别结果

    Examples:

    .. code-block:: python

        import appbuilder
        asr = appbuilder.ASR()
        os.environ["APPBUILDER_TOKEN"] = '...'

        with open("xxxx.pcm", "rb") as f:
            audio_data = f.read()
        content_data = {"audio_format": "pcm", "raw_audio": audio_data, "rate": 16000}
        msg = appbuilder.Message(content_data)
        out = asr.run(msg)
        print(out.content) # eg: {"result": ["北京科技馆。"]}
     """
    @HTTPClient.check_param
    def run(self, message: Message, audio_format: str = "pcm", rate: int = 16000,
            timeout: float = None, retry: int = 0) -> Message:
        """
        输入语音文件并返回语音识别结果。

        参数:
            message (obj:`Message`): 输入消息，用于模型的主要输入内容。这是一个必需的参数。举例: Message(content={"raw_audio": b"..."})。
            audio_format (str，可选): 语音文件的格式，pcm/wav/amr/m4a。不区分大小写。推荐pcm文件。
            rate (int， 可选): 采样率，16000，固定值。
            timeout (float, 可选): HTTP超时时间。
            retry (int, 可选): HTTP重试次数。

        返回:
            obj:`Message`: 短语音识别结果。举例: Message(content={"result": ["北京科技馆。"]})。
        """
        inp = ASRInMsg(**message.content)
        request = ShortSpeechRecognitionRequest()
        request.format = audio_format
        request.rate = rate
        request.cuid = str(uuid.uuid4())
        request.dev_pid = "80001"
        request.speech = inp.raw_audio
        response = self._recognize(request, timeout, retry)
        out = ASROutMsg(result=list(response.result))
        return Message(content=out.model_dump())

    def _recognize(self, request: ShortSpeechRecognitionRequest, timeout: float = None,
                   retry: int = 0) -> ShortSpeechRecognitionResponse:
        """
        使用给定的输入并返回语音识别的结果。

        参数:
            request (obj:`ShortSpeechRecognitionRequest`): 输入请求，这是一个必需的参数。
            timeout (float, 可选): 请求的超时时间。
            retry (int, 可选): 请求的重试次数。

        返回:
            obj:`ShortSpeechRecognitionResponse`: 接口返回的输出消息。
        """
        ContentType = "audio/" + request.format + ";rate=" + str(request.rate)
        headers = self.http_client.auth_header()
        headers['content-type'] = ContentType
        params = {
            'dev_pid': request.dev_pid,
            'cuid': request.cuid
        }
        if retry != self.http_client.retry.total:
            self.http_client.retry.total = retry
        response = self.http_client.session.post(self.http_client.service_url("/v1/bce/aip_speech/asrpro"),
                                                 params=params, headers=headers, data=request.speech, timeout=timeout)
        self.http_client.check_response_header(response)
        data = response.json()
        self.http_client.check_response_json(data)
        request_id = self.http_client.response_request_id(response)
        self.__class__._check_service_error(request_id,data)
        response = ShortSpeechRecognitionResponse.from_json(payload=json.dumps(data))
        response.request_id = request_id
        return response

    @staticmethod
    def _check_service_error(request_id: str, data: dict):
        r"""个性化服务response参数检查

            参数:
                request (dict) : 短语音识别body返回
            返回：
                无
        """
        if "err_no" in data and "err_msg" in data:
            if data["err_no"] != 0:
                raise AppBuilderServerException(
                    request_id=request_id,
                    service_err_code=data["err_no"],
                    service_err_message=data["err_msg"]
                )
