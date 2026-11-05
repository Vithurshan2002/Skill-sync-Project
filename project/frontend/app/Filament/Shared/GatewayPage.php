<?php

namespace App\Filament\Shared;

use App\Contracts\SkillSyncGateway;
use Carbon\Carbon;
use Filament\Notifications\Notification;
use Filament\Pages\Page;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;

abstract class GatewayPage extends Page
{
    protected static string $role = 'customer';

    public ?string $gatewayError = null;

    public static function canAccess(): bool
    {
        return auth()->check() && auth()->user()->role === static::$role;
    }

    protected function gateway(): SkillSyncGateway
    {
        abort_unless(static::canAccess(), 403);

        return app(SkillSyncGateway::class);
    }

    protected function success(string $message): void
    {
        Notification::make()->title($message)->success()->send();
    }

    protected function perform(callable $operation, ?string $statePath = null): mixed
    {
        $this->gatewayError = null;

        try {
            return $operation();
        } catch (ValidationException $exception) {
            if ($statePath) {
                throw ValidationException::withMessages(collect($exception->errors())->mapWithKeys(fn ($messages, $key) => ["{$statePath}.{$key}" => $messages])->all());
            }

            throw $exception;
        } catch (HttpException $exception) {
            if ($exception->getStatusCode() < 500) {
                throw $exception;
            }

            $this->gatewayError = 'The service is temporarily unavailable. Please try again.';
            Notification::make()->title($this->gatewayError)->danger()->send();

            return null;
        }
    }

    protected function categoryOptions(): array
    {
        return collect($this->gateway()->categories()['data'])->pluck('label', 'label')->all();
    }

    public function localDate(?string $value): string
    {
        return $value ? Carbon::parse($value)->timezone('Asia/Colombo')->format('d M Y · g:i A') : 'Not set';
    }
}
