<?php

namespace App\Providers\Filament;

use App\Filament\Shared\InitialsAvatarProvider;
use App\Filament\Shared\NotificationsPage;
use App\Filament\Shared\SettingsPage;
use App\Filament\Shared\WorkspaceStats;
use App\Http\Middleware\BackendSession;
use Filament\FontProviders\LocalFontProvider;
use Filament\Http\Middleware\Authenticate;
use Filament\Http\Middleware\DisableBladeIconComponents;
use Filament\Http\Middleware\DispatchServingFilamentEvent;
use Filament\Navigation\NavigationItem;
use Filament\Panel;
use Filament\PanelProvider;
use Filament\Support\Colors\Color;
use Filament\View\PanelsRenderHook;
use Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse;
use Illuminate\Cookie\Middleware\EncryptCookies;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Illuminate\Routing\Middleware\SubstituteBindings;
use Illuminate\Session\Middleware\StartSession;
use Illuminate\View\Middleware\ShareErrorsFromSession;

abstract class SkillSyncPanelProvider extends PanelProvider
{
    protected function shared(Panel $panel, string $id): Panel
    {
        return $panel
            ->id($id)->path($id)->brandName('SkillSync')
            ->brandLogo(fn () => asset('images/brand/skillsync-logo-v1.png'))->brandLogoHeight('3rem')
            ->homeUrl(fn () => route('home'))->darkMode(false)
            ->colors(['primary' => Color::Indigo, 'success' => Color::Teal])
            ->font('Manrope Variable', provider: LocalFontProvider::class)
            ->defaultAvatarProvider(InitialsAvatarProvider::class)
            ->favicon(asset('favicon.svg'))
            ->viteTheme('resources/css/filament/theme.css')
            ->sidebarCollapsibleOnDesktop()
            ->renderHook(PanelsRenderHook::GLOBAL_SEARCH_AFTER, fn () => view('filament.shared.notification-bell'))
            ->widgets([WorkspaceStats::class])
            ->pages([NotificationsPage::class, SettingsPage::class])
            ->navigationItems([
                NavigationItem::make('Find a professional')->url('/workers')->icon('heroicon-o-magnifying-glass')->sort(90),
            ])
            ->middleware([
                EncryptCookies::class, AddQueuedCookiesToResponse::class, StartSession::class,
                ShareErrorsFromSession::class, ValidateCsrfToken::class, SubstituteBindings::class,
                DisableBladeIconComponents::class, DispatchServingFilamentEvent::class,
            ])->authMiddleware([Authenticate::class, BackendSession::class], isPersistent: true);
    }
}
