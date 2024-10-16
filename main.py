import aiohttp
import asyncio
import time
import os
import logging
from colorama import Fore, Style, init

init(autoreset=True)

class ColoredLogger(logging.Logger):
    colMap = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def __init__(self, name):
        super().__init__(name)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        if self.isEnabledFor(level):
            color = self.colMap.get(logging.getLevelName(level), '')
            msg = f"{color}{msg}{Style.RESET_ALL}"
            super()._log(level, msg, args, exc_info, extra, stack_info)

logging.setLoggerClass(ColoredLogger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def clearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parseProxy(proxy_string, proxyFormat):
    if proxyFormat == '1':  # IP:Port
        return f"http://{proxy_string}"
    elif proxyFormat == '2':#    IP:Port:Username:Password
        parts = proxy_string.split(':')
        if len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    elif proxyFormat == '3':#    Protocol://IP:Port
        return proxy_string if '://' in proxy_string else f"http://{proxy_string}"
    elif proxyFormat == '4':#    Username:Password@IP:Port
        return f"http://{proxy_string}"
    elif proxyFormat == '5':#    Protocol://Username:Password@IP:Port
        return proxy_string if '://' in proxy_string else f"http://{proxy_string}"
    return None

async def checkProxy(session, proxy, semaphore, timeout=5):
    async with semaphore:
        try:
            startTime = time.time()
            async with session.get('http://httpbin.org/ip', proxy=proxy, timeout=timeout) as response:
                endTime = time.time()
                if response.status == 200:
                    resTime = endTime - startTime
                    logger.info(f"Proxy {proxy} is valid. Response time: {resTime:.2f}s")
                    return True, proxy, resTime
                else:
                    logger.warning(f"Proxy {proxy} is invalid. Status code: {response.status}")
                    return False, proxy, None
        except asyncio.TimeoutError:
            logger.error(f"Proxy {proxy} timed out after {timeout}s")
            return False, proxy, None
        except Exception as e:
            logger.error(f"Error checking proxy {proxy}: {str(e)[:100]}")
            return False, proxy, None

async def checkProxies(proxies, max_concurrency=10000, chunk_size=1000):
    semaphore = asyncio.Semaphore(max_concurrency)
    connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        allResults = []
        for i in range(0, len(proxies), chunk_size):
            chunk = proxies[i:i+chunk_size]
            tasks = [checkProxy(session, proxy, semaphore) for proxy in chunk]
            results = await asyncio.gather(*tasks)
            allResults.extend(results)
            logger.info(f"Processed {i+len(chunk)}/{len(proxies)} proxies")
        return allResults

def loadProxies(filePath, proxyFormat):
    with open(filePath, 'r') as file:
        return [parseProxy(line.strip(), proxyFormat) for line in file if line.strip()]

async def main():
    clearScreen()
    logger.info("Proxy-Checker")
    filePath = input(f"{Fore.CYAN}Enter the path to your proxy file: {Style.RESET_ALL}")
    if not os.path.exists(filePath):
        logger.error("File not found. Please check the path and try again.")
        return

    logger.info("Select proxy format:")
    print(f"{Fore.YELLOW}1. IP:Port")
    print(f"{Fore.YELLOW}2. IP:Port:Username:Password")
    print(f"{Fore.YELLOW}3. Protocol://IP:Port")
    print(f"{Fore.YELLOW}4. Username:Password@IP:Port")
    print(f"{Fore.YELLOW}5. Protocol://Username:Password@IP:Port")
    proxyFormat = input(f"{Fore.CYAN}Enter the format number (1-5): {Style.RESET_ALL}")

    if proxyFormat not in ['1', '2', '3', '4', '5']:
        logger.error("Invalid format selection. Please try again.")
        return
    proxies = loadProxies(filePath, proxyFormat)
    if not proxies:
        logger.error("No valid proxies found in the file.")
        return
    logger.info(f"Loaded {len(proxies)} proxies from file.")
    logger.info("Checking proxies...")

    startTime = time.time()
    results = await checkProxies(proxies)
    endTime = time.time()
    
    workingProxies = [result for result in results if result[0]]
    
    logger.info("Summary:")
    logger.info(f"Total proxies: {len(proxies)}")
    logger.info(f"Valid proxies: {len(workingProxies)}")
    logger.info(f"Time taken: {endTime - startTime:.2f} seconds")

    saveOption = input(f"{Fore.CYAN}Do you want to save the valid proxies? (y/n): {Style.RESET_ALL}").lower()
    if saveOption == 'y':
        outFile = input(f"{Fore.CYAN}Enter the output file name (default: workingProxies.txt): {Style.RESET_ALL}") or "workingProxies.txt"
        with open(outFile, 'w') as file:
            for result in workingProxies:
                file.write(f"{result[1]},{result[2]:.2f}\n")
        logger.info(f"Valid proxies have been saved to '{outFile}'")

if __name__ == "__main__":
    asyncio.run(main())
