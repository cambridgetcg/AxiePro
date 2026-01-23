"""
Ronin RPC Mock

Mocks the Ronin blockchain RPC calls used for:
- Wallet balance checks
- Transaction lookups
- Contract interactions
- Block data
"""

from typing import Any, Dict, List, Optional, Union
import respx
from httpx import Response


class RoninRPCMock:
    """Mock for Ronin blockchain RPC calls."""

    BASE_URL = "https://api.roninchain.com/rpc"

    def __init__(self):
        """Initialize the mock."""
        self._routes: List[respx.Route] = []
        self._call_count: int = 0

    def _create_rpc_response(
        self,
        result: Any,
        error: Optional[Dict[str, Any]] = None,
        request_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Create a JSON-RPC 2.0 response.

        Args:
            result: The result data
            error: Optional error object
            request_id: Request ID to echo back

        Returns:
            JSON-RPC response dictionary
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result
        return response

    def mock_get_balance(
        self,
        address: str,
        balance_wei: Union[int, str] = "0x0",
    ) -> respx.Route:
        """
        Mock eth_getBalance RPC call.

        Args:
            address: Wallet address to mock balance for
            balance_wei: Balance in wei (hex string or int)

        Returns:
            respx Route for further customization
        """
        if isinstance(balance_wei, int):
            balance_wei = hex(balance_wei)

        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(balance_wei, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_get_transaction(
        self,
        tx_hash: str,
        tx_data: Optional[Dict[str, Any]] = None,
    ) -> respx.Route:
        """
        Mock eth_getTransactionByHash RPC call.

        Args:
            tx_hash: Transaction hash
            tx_data: Transaction data (auto-generated if None)

        Returns:
            respx Route
        """
        if tx_data is None:
            tx_data = {
                "hash": tx_hash,
                "blockNumber": "0x1234",
                "blockHash": "0x" + "a" * 64,
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": "0x0",
                "gas": "0x5208",
                "gasPrice": "0x3b9aca00",
                "nonce": "0x0",
                "transactionIndex": "0x0",
                "input": "0x",
            }

        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(tx_data, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_transaction_not_found(self) -> respx.Route:
        """
        Mock transaction not found response.

        Returns:
            respx Route
        """
        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(None, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_get_transaction_receipt(
        self,
        tx_hash: str,
        status: int = 1,
        gas_used: str = "0x5208",
    ) -> respx.Route:
        """
        Mock eth_getTransactionReceipt RPC call.

        Args:
            tx_hash: Transaction hash
            status: 1 for success, 0 for failure
            gas_used: Gas used in hex

        Returns:
            respx Route
        """
        receipt = {
            "transactionHash": tx_hash,
            "blockNumber": "0x1234",
            "blockHash": "0x" + "a" * 64,
            "from": "0x" + "1" * 40,
            "to": "0x" + "2" * 40,
            "status": hex(status),
            "gasUsed": gas_used,
            "cumulativeGasUsed": gas_used,
            "logs": [],
            "logsBloom": "0x" + "0" * 512,
            "transactionIndex": "0x0",
        }

        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(receipt, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_get_block_number(self, block_number: int = 12345678) -> respx.Route:
        """
        Mock eth_blockNumber RPC call.

        Args:
            block_number: Current block number

        Returns:
            respx Route
        """
        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(hex(block_number), request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_call(
        self,
        result: str = "0x",
    ) -> respx.Route:
        """
        Mock eth_call RPC call (contract read).

        Args:
            result: Return data in hex

        Returns:
            respx Route
        """
        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(result, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_error(
        self,
        code: int = -32000,
        message: str = "Internal error",
    ) -> respx.Route:
        """
        Mock RPC error response.

        Args:
            code: JSON-RPC error code
            message: Error message

        Returns:
            respx Route
        """
        error = {
            "code": code,
            "message": message,
        }

        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            request_id = data.get("id", 1)
            return Response(
                200,
                json=self._create_rpc_response(None, error=error, request_id=request_id)
            )

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    def mock_connection_error(self) -> respx.Route:
        """
        Mock connection/network error.

        Returns:
            respx Route
        """
        import httpx

        route = respx.post(self.BASE_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        self._routes.append(route)
        return route

    def mock_timeout(self) -> respx.Route:
        """
        Mock request timeout.

        Returns:
            respx Route
        """
        import httpx

        route = respx.post(self.BASE_URL).mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        self._routes.append(route)
        return route

    def mock_batch_request(
        self,
        results: List[Any],
    ) -> respx.Route:
        """
        Mock batch RPC request.

        Args:
            results: List of results for each request in batch

        Returns:
            respx Route
        """
        def response_callback(request):
            self._call_count += 1
            data = request.content
            if isinstance(data, bytes):
                import json
                data = json.loads(data)

            responses = []
            for i, req in enumerate(data):
                result = results[i] if i < len(results) else None
                responses.append(self._create_rpc_response(result, request_id=req.get("id", i)))

            return Response(200, json=responses)

        route = respx.post(self.BASE_URL).mock(side_effect=response_callback)
        self._routes.append(route)
        return route

    @property
    def call_count(self) -> int:
        """Get the number of RPC calls made."""
        return self._call_count

    def reset_call_count(self) -> None:
        """Reset the call counter."""
        self._call_count = 0

    def clear(self) -> None:
        """Clear all mocked routes and reset counters."""
        self._routes.clear()
        self._call_count = 0
