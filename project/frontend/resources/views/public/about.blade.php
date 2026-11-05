<x-layout title="About SkillSync">
    <div class="ss-about-page ss-container">
        <section class="ss-about-intro" aria-labelledby="about-title">
            <div class="ss-about-intro-copy ss-page-heading">
                <span class="ss-eyebrow">ABOUT SKILLSYNC</span>
                <h1 id="about-title">Local skills.<br><em>Everyday solutions.</em></h1>
                <p class="ss-about-lead">SkillSync connects customers with local service professionals across Sri Lanka.</p>
                <p>From a leaking tap to a carpentry job, find the right service, compare professionals in your area, and manage your booking in one place.</p>
                <a class="ss-button ss-button-primary" href="{{ route('workers') }}">Find a professional <x-icon name="heroicon-o-arrow-right" /></a>
            </div>
            <aside class="ss-about-services" aria-labelledby="about-services-title">
                <h2 id="about-services-title">Practical help, close to home.</h2>
                <p>Explore our four service categories.</p>
                <ul>
                    <li><x-service-icon category="Plumbing" /><div><h3>Plumbing</h3><p>Taps, pipes, leaks, and household repairs.</p></div></li>
                    <li><x-service-icon category="Electrical" /><div><h3>Electrical</h3><p>Lighting, wiring, and electrical maintenance.</p></div></li>
                    <li><x-service-icon category="Carpentry" /><div><h3>Carpentry</h3><p>Furniture, fittings, and woodwork.</p></div></li>
                    <li><x-service-icon category="Welding" /><div><h3>Welding</h3><p>Gates, metalwork, and repairs.</p></div></li>
                </ul>
                <a class="ss-text-link" href="{{ route('services') }}">Explore services <x-icon name="heroicon-o-arrow-right" /></a>
            </aside>
        </section>

        <section class="ss-about-process" aria-labelledby="about-process-title">
            <div>
                <span class="ss-eyebrow">HOW IT WORKS</span>
                <h2 id="about-process-title">From your first request to the finished job.</h2>
                <p>Find help, arrange the work, and follow its progress in one place.</p>
            </div>
            <ol class="ss-about-steps" role="list">
                <li>
                    <div class="ss-about-step-icon" aria-hidden="true">
                        <x-icon name="heroicon-o-pencil-square" />
                        <span class="ss-about-step-number">01</span>
                    </div>
                    <span class="ss-about-step-connector" aria-hidden="true"><x-icon name="heroicon-o-arrow-right" /></span>
                    <div class="ss-about-step-copy"><h3>Describe your job</h3><p>Tell us what needs doing, where, and when.</p></div>
                </li>
                <li>
                    <div class="ss-about-step-icon" aria-hidden="true">
                        <x-icon name="heroicon-o-user-circle" />
                        <span class="ss-about-step-number">02</span>
                    </div>
                    <span class="ss-about-step-connector" aria-hidden="true"><x-icon name="heroicon-o-arrow-right" /></span>
                    <div class="ss-about-step-copy"><h3>Choose a professional</h3><p>Compare your matches and send a booking request.</p></div>
                </li>
                <li>
                    <div class="ss-about-step-icon" aria-hidden="true">
                        <x-icon name="heroicon-o-clipboard-document-check" />
                        <span class="ss-about-step-number">03</span>
                    </div>
                    <div class="ss-about-step-copy"><h3>Track and confirm</h3><p>Follow the work, confirm completion, and leave a review.</p></div>
                </li>
            </ol>
        </section>

        <section class="ss-about-community" aria-label="SkillSync for customers and professionals">
            <article class="ss-card">
                <h2>For customers</h2>
                <p>Choose local help with a clearer picture of who you’re booking.</p>
                <ul class="ss-about-benefits">
                    <li><x-icon name="heroicon-o-check" /><span>Browse profiles reviewed by an administrator.</span></li>
                    <li><x-icon name="heroicon-o-check" /><span>Compare rates, work history, and customer reviews.</span></li>
                    <li><x-icon name="heroicon-o-check" /><span>See why each professional matches your request.</span></li>
                </ul>
                <a class="ss-text-link" href="{{ route('workers') }}">Browse professionals <x-icon name="heroicon-o-arrow-right" /></a>
            </article>
            <article class="ss-card">
                <h2>For professionals</h2>
                <p>Bring your skills to local customers and manage your work.</p>
                <ul class="ss-about-benefits">
                    <li><x-icon name="heroicon-o-check" /><span>Set your services, coverage area, and rates.</span></li>
                    <li><x-icon name="heroicon-o-check" /><span>Manage booking requests and keep customers updated.</span></li>
                    <li><x-icon name="heroicon-o-check" /><span>Build your reputation through completed jobs and reviews.</span></li>
                </ul>
                @auth
                    <a class="ss-text-link" href="/{{ auth()->user()->role }}/dashboard">My workspace <x-icon name="heroicon-o-arrow-right" /></a>
                @else
                    <a class="ss-text-link" href="{{ route('register') }}">Join as a professional <x-icon name="heroicon-o-arrow-right" /></a>
                @endauth
            </article>
        </section>
    </div>
</x-layout>
