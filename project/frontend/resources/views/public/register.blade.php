<x-layout title="Create an account">
    <div class="ss-auth-surface">
    <section class="ss-container ss-auth-grid">
        <div class="ss-auth-intro"><span class="ss-eyebrow">LET'S MAKE GOOD THINGS HAPPEN</span><h1>A place for<br><em>your next step.</em></h1><p>Whether you're looking for an extra pair of hands or bringing your skills to the table, start here.</p><div class="ss-auth-quote"><x-icon name="heroicon-o-hand-raised" /><h2>Just exploring?<br>You're in the right place.</h2><p>Create a customer account to request a service, or a worker account to offer your skills.</p></div></div>
        <div class="ss-auth-card">
            <header class="ss-auth-card-header"><h2>Create an account</h2><p>A few details, and you're ready to explore.</p></header>
                <form action="{{ route('register') }}" method="post" class="ss-stack">@csrf
                    @if($errors->any())<div class="ss-alert ss-alert-error" role="alert" tabindex="-1" autofocus>Please check the highlighted fields below.</div>@endif
                    <fieldset class="ss-role-fieldset"><legend>I'm here to…</legend><div><label><input type="radio" name="role" value="customer" @checked(old('role', request('role', 'customer')) === 'customer') @error('role') aria-invalid="true" aria-describedby="role-error" @enderror><span><x-icon name="heroicon-o-magnifying-glass" />Find a specialist</span></label><label><input type="radio" name="role" value="worker" @checked(old('role', request('role', 'customer')) === 'worker') @error('role') aria-invalid="true" aria-describedby="role-error" @enderror><span><x-icon name="heroicon-o-wrench-screwdriver" />Offer my skills</span></label></div>@error('role')<p class="ss-field-error" id="role-error">{{ $message }}</p>@enderror</fieldset>
                    <div class="ss-field"><label for="name">Name</label><input class="ss-input" id="name" name="name" value="{{ old('name') }}" placeholder="Your name" required minlength="2" maxlength="100" @error('name') aria-invalid="true" aria-describedby="name-error" @enderror>@error('name')<p class="ss-field-error" id="name-error">{{ $message }}</p>@enderror</div>
                    <div class="ss-field"><label for="register-email">Email address</label><input class="ss-input" type="email" id="register-email" name="email" value="{{ old('email') }}" placeholder="alex@example.com" autocomplete="username" maxlength="254" required @error('email') aria-invalid="true" aria-describedby="register-email-error" @enderror>@error('email')<p class="ss-field-error" id="register-email-error">{{ $message }}</p>@enderror</div>
                    <div class="ss-field">
                        <label for="town">Town</label>
                        <div class="ss-filter-select">
                            <select id="town" name="town" class="ss-input" required @error('town') aria-invalid="true" aria-describedby="town-error" @enderror><option value="">Select a town</option>@foreach(['Colombo', 'Galle', 'Jaffna', 'Kandy'] as $town)<option value="{{ $town }}" @selected(old('town') === $town)>{{ $town }}</option>@endforeach</select>
                            <x-icon name="heroicon-o-chevron-down" aria-hidden="true" />
                        </div>
                        @error('town')<p class="ss-field-error" id="town-error">{{ $message }}</p>@enderror
                    </div>
                    <div class="ss-form-columns"><div class="ss-field"><label for="register-password">Password</label><div class="ss-password-field"><input class="ss-input" id="register-password" name="password" type="password" minlength="8" maxlength="128" placeholder="At least 8 characters" autocomplete="new-password" required @error('password') aria-invalid="true" aria-describedby="register-password-error" @enderror><x-password-toggle target="register-password" /></div>@error('password')<p class="ss-field-error" id="register-password-error">{{ $message }}</p>@enderror</div><div class="ss-field"><label for="password-confirmation">Confirm password</label><div class="ss-password-field"><input class="ss-input" id="password-confirmation" name="password_confirmation" type="password" minlength="8" maxlength="128" autocomplete="new-password" required @error('password_confirmation') aria-invalid="true" aria-describedby="password-confirmation-error" @enderror><x-password-toggle target="password-confirmation" label="confirm password" /></div>@error('password_confirmation')<p class="ss-field-error" id="password-confirmation-error">{{ $message }}</p>@enderror</div></div>
                    <button class="ss-button ss-button-primary ss-button-full ss-auth-submit" type="submit" data-loading-label="Creating account…"><span data-submit-label aria-live="polite">Create account</span><x-icon name="heroicon-o-arrow-right" /></button>
                </form><p class="ss-auth-footer">Already have an account? <a href="{{ route('login') }}">Log in</a></p>
        </div>
    </section>
    </div>
</x-layout>
