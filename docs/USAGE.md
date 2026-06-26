# End-User Usage Guide - Python REST API Echo Server

This guide explains how to interact with the deployed echo service to diagnose network requests, mock statuses, verify payloads, and perform standard health telemetry.

For the live deployed URL of this microservice, please refer to the **Deployment** section in the main [README.md](../README.md).

---

## Service Endpoints

### 1. Health Status (`GET /health`)
Returns the system health status along with the total container uptime (in seconds).

- **Request Method**: `GET`
- **URL Path**: `/health`
- **Example Request**:
  ```sh
  curl -i http://localhost:8080/health
  ```
- **Example Success Response (HTTP 200)**:
  ```json
  {
    "status": "healthy",
    "uptime_seconds": 45.321894
  }
  ```

---

### 2. Request Echo Service (`/echo`)
Mirrors the HTTP request method, request headers, parsed query variables, and decoded body bytes back to the caller.

- **Supported HTTP Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **URL Path**: `/echo`

#### Query Parameter Handling rules
- **Single parameter** maps to a single string value: `?param=value` &rarr; `"param": "value"`
- **Duplicate parameters** map to an array of strings: `?param=val1&param=val2` &rarr; `"param": ["val1", "val2"]`
- **Empty parameter** after the equals sign maps to an empty string: `?param=` &rarr; `"param": ""`

#### Mocking Responses using `X-Echo-Status`
You can override the response status code by providing an integer value between `100` and `599` in the `X-Echo-Status` header.
- **Invalid values** (e.g., non-integers, floats like `200.5`, booleans like `True`, or integers outside the `100-599` range) will cause the server to reject the request with `HTTP 400 Bad Request` instantly.

#### Echo Invocation Examples

**Example A: Simple Echo with Custom Status Override**
```sh
curl -i -H "X-Echo-Status: 201" \
     "http://localhost:8080/echo?a=1&b=&a=2"
```
- **Response (HTTP 201 Created)**:
  ```json
  {
    "method": "GET",
    "headers": {
      "host": "localhost:8080",
      "user-agent": "curl/7.81.0",
      "accept": "*/*",
      "x-echo-status": "201"
    },
    "query_params": {
      "a": ["1", "2"],
      "b": ""
    },
    "body": ""
  }
  ```

**Example B: POST Request with JSON Body**
```sh
curl -i -X POST \
     -H "Content-Type: application/json" \
     -d '{"event": "test", "data": 42}' \
     "http://localhost:8080/echo"
```
- **Response (HTTP 200 OK)**:
  ```json
  {
    "method": "POST",
    "headers": {
      "host": "localhost:8080",
      "content-length": "31",
      "content-type": "application/json",
      "user-agent": "curl/7.81.0",
      "accept": "*/*"
    },
    "query_params": {},
    "body": "{\"event\": \"test\", \"data\": 42}"
  }
  ```

---

## Edge Cases & Error Behaviors

### 1. Payload Too Large (HTTP 413)
If the payload size exceeds the configured max limit (exactly `5242880` bytes / 5.0 MB by default), the application halts reading immediately and returns a payload error to avoid memory overhead.
- **Error Response (HTTP 413 Payload Too Large)**:
  ```json
  {
    "detail": "Payload Too Large"
  }
  ```

### 2. Invalid Content-Length Header (HTTP 400)
Providing an invalid `Content-Length` header (such as strings, floats, booleans, or negative values) is checked before parsing and rejected immediately.
- **Error Response (HTTP 400 Bad Request)**:
  ```json
  {
    "detail": "Invalid Content-Length"
  }
  ```

### 3. Invalid Mock Code Header (HTTP 400)
Providing a non-integer or out-of-bounds `X-Echo-Status` header returns a bad request detail.
- **Error Response (HTTP 400 Bad Request)**:
  ```json
  {
    "detail": "Invalid X-Echo-Status"
  }
  ```