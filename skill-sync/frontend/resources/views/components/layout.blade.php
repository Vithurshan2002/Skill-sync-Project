@props(['title' => 'Find the right skills. Book with confidence.'])
<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <meta name="description" content="Find local professionals, compare their services, and manage your bookings with SkillSync.">
    <meta name="theme-color" content="#4338ca">
    <title>{{ $title }} · SkillSync</title>
    <link rel="icon" href="{{ asset('favicon.svg') }}" type="image/svg+xml">
    @vite(['resources/css/app.css', 'resources/js/app.js'])
    @livewireStyles
</head>
<body class="ss-site">
    <a href="#main-content" class="ss-skip">Skip to content</a>
    <header class="ss-header" x-data="{ open: false }">
        <div class="ss-container ss-nav">
            <a class="ss-brand" href="{{ route('home') }}" aria-label="SkillSync home"><img class="ss-brand-logo" src="{{ asset('images/brand/skillsync-logo-v1.png') }}" alt="SkillSync" width="2172" height="724"></a>
            <nav class="ss-desktop-nav" aria-label="Main navigation">
                <a href="{{ route('home') }}" @class(['is-active' => request()->is('/')])>Home</a>
                <a href="{{ route('services') }}" @class(['is-active' => request()->is('services')])>Explore services</a>
                <a href="{{ route('workers') }}" @class(['is-active' => request()->is('workers*')])>Find a professional</a>
                <a href="{{ route('about') }}" @class(['is-active' => request()->is('about')])>About us</a>
            </nav>
            <div class="ss-nav-actions">
                @auth
                    <livewire:shared.notification-bell />
                    <form method="post" action="{{ route('logout') }}" class="ss-header-logout" x-data="{ signingOut: false }" @submit="if (signingOut) { $event.preventDefault() } else { signingOut = true }">
                        @csrf
                        <button type="submit" class="ss-login-link" :disabled="signingOut" :aria-busy="signingOut" x-text="signingOut ? 'Logging out…' : 'Log out'">Log out</button>
                    </form>
                    
                    <a class="ss-button ss-button-primary ss-button-small" href="/{{ auth()->user()->role }}/dashboard">My workspace <x-filament::icon icon="heroicon-m-arrow-up-right" /></a>
                @else
                    <a class="ss-login-link" href="{{ route('login') }}">Log in</a>
                    <a class="ss-button ss-button-primary ss-button-small" href="{{ route('register') }}">Get started <x-filament::icon icon="heroicon-m-arrow-up-right" /></a>
                @endauth
                <button class="ss-menu-button ss-icon-button" @click="open = !open" :aria-expanded="open" aria-controls="mobile-navigation" aria-label="Toggle navigation"><x-filament::icon icon="heroicon-o-bars-3" /></button>
            </div>
        </div>
        <nav id="mobile-navigation" class="ss-mobile-nav" x-show="open" x-cloak @keydown.escape.window="open = false" aria-label="Mobile navigation">
            <a href="/">Home</a><a href="/services">Explore services</a><a href="/workers">Find a professional</a><a href="/about">About us</a><a href="{{ auth()->check() ? route('settings') : route('login') }}">{{ auth()->check() ? 'My account' : 'Log in' }}</a>
            @auth <a href="/{{ auth()->user()->role }}/dashboard">My workspace</a><a href="/settings">Settings</a> @endauth
            @auth
                <form method="post" action="{{ route('logout') }}" class="ss-mobile-logout" x-data="{ signingOut: false }" @submit="if (signingOut) { $event.preventDefault() } else { signingOut = true }">
                    @csrf
                    <button type="submit" :disabled="signingOut" :aria-busy="signingOut" x-text="signingOut ? 'Logging out…' : 'Log out'">Log out</button>
                </form>
            @endauth
            @auth
                
            @endauth
        </nav>
    </header>
    <main id="main-content" tabindex="-1">
        @if(session('success') || session('status'))
            @if(session('status') === 'You are signed out.' && ! session('success'))
                <div class="ss-container ss-flash" x-data="{ visible: true }" x-show="visible" x-init="setTimeout(() => visible = false, 5000)">
                    <div class="ss-alert ss-alert-success ss-signout-message">
                        <span role="status">{{ session('status') }}</span>
                        <button type="button" class="ss-icon-button" aria-label="Dismiss sign out message" @click="visible = false"><x-filament::icon icon="heroicon-o-x-mark" /></button>
                    </div>
                </div>
            @else
                <div class="ss-container ss-flash"><div class="ss-alert ss-alert-success" role="status">{{ session('success') ?? session('status') }}</div></div>
            @endif
        @endif
        {{ $slot }}
    </main>
    <footer class="ss-footer">
        <div class="ss-container ss-footer-main"><div><a class="ss-brand" href="/" aria-label="SkillSync home"><img class="ss-brand-logo" src="{{ asset('images/brand/skillsync-logo-v1.png') }}" alt="SkillSync" width="2172" height="724"></a><p>Local skills. Clear choices. Better connections.</p></div><nav aria-label="Footer navigation"><a href="/services">Services</a><a href="/workers">Professionals</a><a href="/about">About us</a><a href="/login">Get started</a></nav></div>
        <div class="ss-container ss-footer-bottom"><span>© {{ now()->year }} SkillSync. Local services, connected.</span><span>Made for communities in Sri Lanka <span class="ss-footer-dot"></span></span></div>
    </footer>
    @livewireScripts
</body>
</html>
