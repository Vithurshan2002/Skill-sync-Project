<?php

return [
    'fastapi_base_url' => env('FASTAPI_BASE_URL', 'http://127.0.0.1:8101'),
    'timeout' => (int) env('SKILLSYNC_API_TIMEOUT', 25),
    'connect_timeout' => (int) env('SKILLSYNC_API_CONNECT_TIMEOUT', 3),
];
