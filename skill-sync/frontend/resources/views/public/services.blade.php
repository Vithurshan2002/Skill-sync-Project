<x-layout title="Explore services">
    <section class="ss-page-heading ss-container"><span class="ss-eyebrow">THE RIGHT SKILL FOR EVERY JOB</span><h1>Everyday problems.<br><em>Capable hands.</em></h1><p>Explore Plumbing, Electrical, Carpentry, and Welding, then tell us what needs doing.</p></section>
    <section class="ss-container ss-section ss-section-tight">
        @isset($serviceError)<div class="ss-alert ss-alert-error" role="alert">{{ $serviceError }} <a href="{{ route('services') }}">Try again</a></div>@endisset
        <div class="ss-services-grid">@foreach($categories as $category)<article class="ss-service-card"><span class="ss-category-icon"><x-service-icon :category="$category['label']" /></span><h2>{{ $category['label'] }}</h2><p>{{ $category['description'] }}</p><div class="ss-service-example"><span>FOR EXAMPLE</span><p>“{{ $category['exampleRequest'] }}”</p></div><a class="ss-text-link" href="{{ route('workers', ['category' => $category['label']]) }}">Find a specialist <x-icon name="heroicon-o-arrow-right" /></a></article>@endforeach</div>
    </section>
</x-layout>
