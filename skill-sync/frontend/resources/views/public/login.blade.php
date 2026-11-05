<x-layout title="Welcome back">
    <div class="ss-auth-surface">
    <section class="ss-container ss-auth-grid">
        <div class="ss-auth-intro"><span class="ss-eyebrow">GOOD TO SEE YOU</span><h1>Your next good<br>connection <em>starts here.</em></h1><p>Find the help you need. Or be the person who makes someone's day easier.</p><div class="ss-auth-quote"><x-icon name="heroicon-o-user-group" /><h2>One platform.<br>Both sides of the story.</h2><p>Manage your requests, respond to bookings, and follow every job from start to finish.</p></div></div>
        <div class="ss-auth-card">
            <header class="ss-auth-card-header"><h2>Welcome to SkillSync</h2><p>Log in to your account.</p></header>
            <form method="post" action="{{ route('login') }}" class="ss-stack">@csrf
                <div class="ss-field"><label for="email">Email address</label><input class="ss-input" id="email" name="email" type="email" value="{{ old('email') }}" placeholder="Enter your email address" autocomplete="username" required @error('email') aria-invalid="true" aria-describedby="email-error" @enderror>@error('email')<p class="ss-field-error" id="email-error">{{ $message }}</p>@enderror</div>
                <div class="ss-field"><label for="password">Password</label><div class="ss-password-field"><input class="ss-input" id="password" name="password" type="password" placeholder="Enter your password" autocomplete="current-password" maxlength="128" required @error('password') aria-invalid="true" aria-describedby="password-error" @enderror><x-password-toggle target="password" /></div>@error('password')<p class="ss-field-error" id="password-error">{{ $message }}</p>@enderror</div>
                <button class="ss-button ss-button-primary ss-button-full ss-auth-submit" type="submit" data-loading-label="Logging in…"><span data-submit-label aria-live="polite">Log in</span><x-icon name="heroicon-o-arrow-right" /></button>
            </form><p class="ss-auth-footer">New here? <a href="{{ route('register') }}">Create an account</a></p>
        </div>
    </section>
    </div>
</x-layout>
