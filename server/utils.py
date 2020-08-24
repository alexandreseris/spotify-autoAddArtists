import random
import string
import requests
import traceback
import base64
import time


def generateRandomString(length=50):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


def b64(string, encoding="utf8"):
    strRawEncod = string.encode(encoding)
    b64Bytes = base64.b64encode(strRawEncod)
    return b64Bytes.decode(encoding)


def request(url,
            method="get",
            headers=None,
            params=None,
            body=None,
            json=None,
            verbose=False,
            pauseOnErr=False,
            exceptionCatch=Exception,
            numberOfCall=1,
            secondsToWaitAfterReq=0,
            **kwargs):
    reqDetails = "appel {numberOfCall} de {method} {url}\nheaders: {headers}\nparams: {params}\nbody: {body}\nautres args: {kwargs}".format(
        **{
            "numberOfCall": str(numberOfCall),
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "body": body,
            "kwargs": kwargs
        })
    if verbose:
        print(reqDetails)
    try:
        with requests.request(method,
                              url,
                              headers=headers,
                              params=params,
                              data=body,
                              json=json,
                              **kwargs) as reqH:
            if secondsToWaitAfterReq > 0:
                time.sleep(secondsToWaitAfterReq)
            statusCode = reqH.status_code
            if verbose:
                print("code retour {} pour {}".format(str(statusCode), reqH.url))
            responseHeaders = reqH.headers
            if int(statusCode / 100) in (4, 5):
                raise ValueError("code retour: " + str(statusCode) + ",\n" +
                                 str(reqH.text))
            else:
                return reqH
    except exceptionCatch as err:
        if statusCode == 429:
            print("rate limit atteind pour\n" + reqDetails)
            secondToWait = int(responseHeaders["Retry-After"]) + 1
            print("attente de " + str(secondToWait) + " secondes")
            time.sleep(secondToWait)
            return request(url,
                           method=method,
                           headers=headers,
                           params=params,
                           body=body,
                           json=json,
                           verbose=verbose,
                           pauseOnErr=pauseOnErr,
                           exceptionCatch=exceptionCatch,
                           numberOfCall=numberOfCall,
                           secondsToWaitAfterReq=secondsToWaitAfterReq,
                           **kwargs)
        if not verbose:
            print(reqDetails)
        tb = traceback.format_exc()
        print("\n" + tb)
        if pauseOnErr:
            input()
        raise err


def loopPerStep(iterable, step):
    if len(iterable) == 0:
        yield iterable
    else:
        n = 0
        for ind, elem in enumerate(iterable):
            if ind % step == 0 and ind != 0:
                yield iterable[n:ind]
                n = ind
        yield iterable[n:ind + 1]


if __name__ == '__main__':
    iterable = [x for x in range(1, 31)]
    print(iterable)
    print(*[str(x) for x in loopPerStep(iterable, 10)], sep="\n")
    iterable = [x for x in range(1, 25)]
    print(iterable)
    print(*[str(x) for x in loopPerStep(iterable, 10)], sep="\n")
