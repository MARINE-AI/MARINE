import asyncio
from typing import Dict, List

class EventBroadcaster:
    def __init__(self):
        self.connections: Dict[str, List[asyncio.Queue]] = {}

    async def subscribe(self, user_email: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if user_email in self.connections:
            self.connections[user_email].append(queue)
        else:
            self.connections[user_email] = [queue]
        return queue

    async def unsubscribe(self, user_email: str, queue: asyncio.Queue):
        if user_email in self.connections:
            self.connections[user_email].remove(queue)
            if not self.connections[user_email]:
                del self.connections[user_email]

    async def broadcast(self, user_email: str, message: str):
        if user_email in self.connections:
            for queue in self.connections[user_email]:
                await queue.put(message)

broadcaster = EventBroadcaster()
