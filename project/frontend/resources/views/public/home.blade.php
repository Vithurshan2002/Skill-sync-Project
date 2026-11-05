<x-layout title="Find the right skills. Book with confidence.">
    <section class="ss-hero ss-container">
        <div class="ss-hero-copy">
            <div class="ss-eyebrow"><span class="ss-eyebrow-line"></span> LOCAL SKILLS. LESS GUESSWORK.</div>
            <h1 class="ss-display">Good work starts<br>with the <em>right person.</em></h1>
            <p class="ss-lead">From a leaking tap to a broken cupboard door. Find skilled people nearby, understand your match, and book with confidence.</p>
            <form action="/customer/requests/new" method="get" class="ss-request-entry">
                <label for="home-request" class="ss-sr-only">What do you need help with?</label>
                <x-icon name="heroicon-o-magnifying-glass" />
                <input id="home-request" name="description" placeholder="What do you need help with?" maxlength="2000">
                <button class="ss-button ss-button-primary" type="submit">Find my specialist <x-icon name="heroicon-o-arrow-right" /></button>
            </form>
            <div class="ss-popular"><span>Try:</span><a href="/customer/requests/new?description={{ urlencode('My kitchen tap keeps leaking even when it is closed.') }}">Leaking tap</a><a href="/workers?category=Electrical">Electrical work</a><a href="/workers?category=Welding">Welding</a></div>
            <div class="ss-hero-assurance"><x-icon name="heroicon-o-check-circle" /><span>Clear profiles</span><span class="ss-dot">·</span><span>Explainable matches</span><span class="ss-dot">·</span><span>Track your booking</span></div>
        </div>
        <div class="ss-hero-visual" aria-label="Featured professional">
            <div class="ss-orbit ss-orbit-one"></div><div class="ss-orbit ss-orbit-two"></div>
            <div class="ss-tool-tile ss-tool-one"><x-service-icon category="Plumbing" /></div>
            <div class="ss-tool-tile ss-tool-two"><x-service-icon category="Electrical" /></div>
            <div class="ss-tool-tile ss-tool-three"><x-service-icon category="Carpentry" /></div>
            <div class="ss-match-preview">
                @if(!empty($preview))
                <div class="ss-match-top"><span class="ss-tiny-label">MEET A LOCAL PROFESSIONAL</span><img class="ss-preview-brand-logo" src="{{ asset('images/brand/skillsync-logo-v1.png') }}" alt="SkillSync" width="2172" height="724"></div>
                <div class="ss-match-request"><span class="ss-round-icon"><x-icon name="heroicon-o-wrench" /></span><div><span>Available service</span><strong>{{ $preview['categories'][0] ?? 'Local services' }}</strong></div><x-icon name="heroicon-o-check-circle" /></div>
                <div class="ss-match-divider"><span></span><span>MEET YOUR SPECIALIST</span><span></span></div>
                <div class="ss-match-person"><span class="ss-avatar ss-avatar-2">{{ collect(explode(' ', $preview['name']))->take(2)->map(fn ($part) => mb_substr($part, 0, 1))->join('') }}</span><div><strong>{{ $preview['name'] }}</strong><span>{{ $preview['categories'][0] }} · {{ $preview['town'] }}</span></div><span class="ss-match-rating"><x-icon name="heroicon-s-star" />{{ $preview['rating'] !== null ? number_format($preview['rating'], 1) : 'New' }}</span></div>
                <div class="ss-match-metrics"><div><strong>{{ $preview['yearsExperience'] }}</strong><span>Years of experience</span></div><div><strong>{{ $preview['reviewCount'] }}</strong><span>Customer reviews</span></div></div>
                <div class="ss-match-reason"><x-icon name="heroicon-o-check" />Offers {{ $preview['categories'][0] }} services in {{ $preview['town'] }}</div>
                <div class="ss-match-reason"><x-icon name="heroicon-o-check" />{{ collect($preview['performance'])->sum('completedJobs') }} completed jobs</div>
                <a class="ss-button ss-button-primary ss-button-full" href="{{ route('workers.show', $preview['id']) }}">Get to know {{ explode(' ', $preview['name'])[0] }} <x-icon name="heroicon-o-arrow-right" /></a>
                <span class="ss-match-footnote">View services, rates, and availability</span>
                @else
                    <span class="ss-eyebrow">MEET A LOCAL PROFESSIONAL</span><h2>Local skills.<br>Clearer choices.</h2><p>Explore specialist profiles and see the reasons behind each recommendation.</p><a class="ss-button ss-button-primary" href="{{ route('workers') }}">Explore the directory <x-icon name="heroicon-o-arrow-right" /></a>
                @endif
            </div>
            <div class="ss-match-float"><span class="ss-round-icon"><x-icon name="heroicon-o-clipboard-document-list" /></span><div><strong>A match that makes sense.</strong><span>See the reasons behind every suggestion.</span></div></div>
        </div>
    </section>

    <div class="ss-benefit-strip"><div class="ss-container"><span><x-icon name="heroicon-o-squares-2x2" />4 specialist service categories</span><span><x-icon name="heroicon-o-map-pin" />Local talent, closer to home</span><span><x-icon name="heroicon-o-chat-bubble-left-ellipsis" />Understand why a worker fits</span></div></div>

    <section class="ss-section ss-container" aria-labelledby="services-heading">
        <div class="ss-section-heading"><div><span class="ss-eyebrow">A LITTLE HELP GOES A LONG WAY</span><h2 id="services-heading">What needs doing?</h2><p>Big fixes, small improvements, and everything in between.</p></div><a href="{{ route('services') }}" class="ss-text-link">Explore all services <x-icon name="heroicon-o-arrow-right" /></a></div>
        @isset($serviceError)<div class="ss-alert ss-alert-error" role="alert">{{ $serviceError }} <a href="{{ route('home') }}">Try again</a></div>@endisset
        <div class="ss-category-grid">
            @foreach($categories as $category)
                <a class="ss-category-card" href="{{ route('workers', ['category' => $category['label']]) }}"><span class="ss-category-icon"><x-service-icon :category="$category['label']" /></span><h3>{{ $category['label'] }}</h3><span class="ss-category-arrow"><x-icon name="heroicon-o-arrow-up-right" /></span></a>
            @endforeach
        </div>
    </section>

    <section class="ss-how-section"><div class="ss-container ss-section">
        <div class="ss-section-heading"><div><span class="ss-eyebrow">FROM TO-DO TO DONE</span><h2>One less thing on your list.</h2></div><p>A simple path to the help you need.<br>You're in control at every step.</p></div>
        <div class="ss-step-grid">
            <div class="ss-step-card"><span class="ss-step-number">01</span><span class="ss-round-icon"><x-icon name="heroicon-o-pencil-square" /></span><h3>Tell us what you need</h3><p>A few details about the job, where you are, and a time that works for you.</p></div>
            <div class="ss-step-card"><span class="ss-step-number">02</span><span class="ss-round-icon"><x-icon name="heroicon-o-user-group" /></span><h3>Find your kind of specialist</h3><p>Explore profiles, compare rates and reviews, and see why each person fits.</p></div>
            <div class="ss-step-card"><span class="ss-step-number">03</span><span class="ss-round-icon"><x-icon name="heroicon-o-calendar-days" /></span><h3>Book. Track. Breathe easy.</h3><p>Send a booking request, follow its progress, and share your experience.</p></div>
        </div>
    </div></section>

    <section class="ss-section ss-container" aria-labelledby="workers-heading">
        <div class="ss-section-heading"><div><span class="ss-eyebrow">PUT A NAME TO THE SKILL</span><h2 id="workers-heading">Good people. Useful skills.</h2><p>Meet available specialists from our community.</p></div><a href="{{ route('workers') }}" class="ss-text-link">Browse specialists <x-icon name="heroicon-o-arrow-right" /></a></div>
        <div class="ss-worker-grid">@forelse($workers as $worker)<x-worker-card :worker="$worker" />@empty<p>No available professionals yet. Please check back soon.</p>@endforelse</div>
        <p class="ss-section-note"><x-icon name="heroicon-o-information-circle" />Profiles reflect registered workers. Reviews come from completed bookings.</p>
    </section>

    <section class="ss-container ss-bottom-cta"><div><span class="ss-eyebrow">GOOD AT WHAT YOU DO?</span><h2>Make your skills<br>someone's solution.</h2><p>Explore the worker experience. Build your profile, manage jobs, and see your work in one place.</p></div><a class="ss-button ss-button-white" href="{{ route('register', ['role' => 'worker']) }}">Join as a specialist <x-icon name="heroicon-o-arrow-up-right" /></a></section>
</x-layout>
