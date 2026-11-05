@props(['category'])
<svg {{ $attributes->class(['ss-icon', 'ss-service-icon']) }} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    @switch(strtolower(trim($category)))
        @case('plumbing')
            <path d="M3 10v8m0-6h7V9h6v3h1a4 4 0 0 1 4 4v1h-5v-1h-6v-1H3M13 9V5m-4 0h8" />
            <path d="M18.5 19s-1.5 1.5-1.5 2a1.5 1.5 0 0 0 3 0c0-.5-1.5-2-1.5-2Z" />
            @break
        @case('electrical')
            <path d="M8 3v5m8-5v5M6 8h12v3a6 6 0 0 1-12 0V8Zm6 9v2a3 3 0 0 1-3 3H6" />
            <path d="m12.5 9.5-2 3H13l-1.5 2" />
            @break
        @case('carpentry')
            <path d="M4 4h10c3 0 5 2 6 5l-5-2-2 2H4V4Zm5 5v11h4V9M9 17h4" />
            @break
        @case('welding')
            <path d="M7 3h10l3 4v8l-4 6H8l-4-6V7l3-4Z" />
            <path d="M7 7h10v6H7zM9 17h6m-6 2h6M4 9H2v4h2m16-4h2v4h-2" />
            @break
        @default
            <path d="M5 5h5v5H5zM14 5h5v5h-5zM5 14h5v5H5zM14 14h5v5h-5z" />
    @endswitch
</svg>
