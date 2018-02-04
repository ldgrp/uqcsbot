from typing import List, Iterable, AsyncIterable, AsyncGenerator, Generator, Any
from functools import partial
from slackclient import SlackClient
import asyncio


# see https://api.slack.com/docs/pagination for details
def paginate_api_call(client: SlackClient, method: str, **kwargs) -> List[dict]:
    return list(Paginator(client, method, **kwargs))


class Channel(object):
    def __init__(self, client: SlackClient, channel_id: str):
        self.client = client
        self.id = channel_id

    def get_members(self) -> List[str]:
        member_pages = paginate_api_call(self.client, "conversations.members", channel=self.id)
        members = []
        for page in member_pages:
            members += page["members"]
        return members


class Paginator(Iterable[dict], AsyncIterable[dict]):
    def __init__(self, client, method, **kwargs):
        self._client = client
        self._method = method
        self._kwargs = kwargs

    def _gen(self) -> Generator[dict, Any, None]:
        kwargs = self._kwargs.copy()
        while kwargs.get("cursor") != "":
            page = self._client.api_call(self._method, **self._kwargs)
            yield page
            kwargs["cursor"] = page.get('response_metadata', {}).get('next_cursor', "")

    def __iter__(self):
        return self._gen()

    async def _agen(self):
        loop = asyncio.get_event_loop()
        kwargs = self._kwargs.copy()
        request_fn = partial(self._client.api_call, self._method, **kwargs)
        while kwargs.get("cursor") != "":
            page = await loop.run_in_executor(None, request_fn)
            yield page
            kwargs["cursor"] = page.get('response_metadata', {}).get('next_cursor', "")

    def __aiter__(self) -> AsyncGenerator[dict, Any, None]:
        return self._agen()


class APIMethodProxy(object):
    """
    Helper class used to implement APIWrapper
    """
    def __init__(self, client: SlackClient, method: str, is_async: bool = False):
        self._client = client
        self._method = method
        self._async = is_async

    def __call__(self, **kwargs) -> dict:
        """
        Perform the relevant API request. Equivalent to SlackClient.api_call
        except the `method` argument is filled in.

        If the APIMethodProxy was constructed with `is_async=True` runs the
        request asynchronously via:
            asyncio.get_event_loop().run_in_executor(None, req)
        """
        fn = partial(
            self._client.api_call,
            self._method,
            **kwargs
        )
        if self._async:
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(None, fn)
        else:
            return fn()

    def paginate(self, **kwargs) -> Paginator:
        return Paginator(self._client, self._method, **kwargs)

    def __getattr__(self, item) -> 'APIMethodProxy':
        """
        Gets another APIMethodProxy with the same configuration as the current
        one, except the attribute that you tried to get is appended to the
        method of the source APIMethodProxy, with a dot separating them.

        For example,
            > APIMethodProxy("chat").postMessage
        is equivalent to
            > APIMethodProxy("chat.postMessage")
        """
        return APIMethodProxy(
            client=self._client,
            method=f'{self._method}.{item}',
            is_async=self._async,
        )


class APIWrapper(object):
    """
    Wraps the Slack API client to make it possible to use dotted methods. Can
    perform API requests both synchronously and asynchronously.

    Example usage:
        > api = APIWrapper(client)
        > api.chat.postMessage(channel="general", text="message")

        > async_api = APIWrapper(client, True)
        > await async_api.chat.postMessage(channel="general", text="message")

        > async_api = api(is_async=True)
        > await async_api.chat.postMessage(channel="general", text="message")
    """
    def __init__(self, client: SlackClient, is_async: bool = False):
        self._client = client
        self._async = is_async

    def __getattr__(self, item) -> APIMethodProxy:
        return APIMethodProxy(
            client=self._client,
            method=item,
            is_async=self._async
        )

    def __call__(self, **kwargs) -> 'APIWrapper':
        """
        On call, reconfigure the API Wrapper
        """
        return type(self)(self._client, **kwargs)