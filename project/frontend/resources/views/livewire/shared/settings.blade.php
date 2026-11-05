<section class="ss-settings-page ss-workspace-settings" aria-labelledby="account-title">
    <section class="ss-card ss-account-card">
        <div class="ss-account-content">
            <header class="ss-account-heading">
                <span class="ss-account-icon"><x-icon name="heroicon-o-user-circle" /></span>
                <div>
                    <h2 id="account-title">Your account</h2>
                    <p>Your account details for this workspace.</p>
                </div>
                @if(in_array(auth()->user()->role, ['customer', 'worker'], true))
                    <a class="ss-button ss-button-secondary ss-account-edit" href="{{ route('filament.'.auth()->user()->role.'.pages.profile', [], false) }}">
                        <x-icon name="heroicon-o-pencil-square" />
                        Edit profile
                    </a>
                @endif
            </header>
            <dl class="ss-settings-details ss-account-details">
                <div><dt>Name</dt><dd>{{ auth()->user()->name }}</dd></div>
                <div><dt>Email address</dt><dd>{{ auth()->user()->email }}</dd></div>
                <div><dt>Account role</dt><dd><span class="ss-account-role">{{ auth()->user()->role === 'admin' ? 'Administrator' : ucfirst(auth()->user()->role) }}</span></dd></div>
            </dl>
        </div>
        <section class="ss-account-session" aria-labelledby="session-title">
            <div>
                <h3 id="session-title">Current session</h3>
                <p>Log out of SkillSync on this browser. Your saved records will remain available.</p>
            </div>
            <form method="POST" action="{{ route('logout') }}">
                @csrf
                <button class="ss-button ss-button-secondary ss-account-logout" type="submit">
                    <x-icon name="heroicon-o-arrow-right-start-on-rectangle" />
                    Log out
                </button>
            </form>
        </section>
    </section>
</section>
