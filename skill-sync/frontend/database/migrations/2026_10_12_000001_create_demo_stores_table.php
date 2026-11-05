<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('demo_stores', function (Blueprint $table) {
            $table->string('id')->primary();
            $table->unsignedInteger('schema_version');
            $table->longText('payload');
            $table->timestamps();
        });

        Schema::table('users', function (Blueprint $table) {
            $table->string('demo_id')->nullable()->unique();
            $table->string('role')->default('customer');
            $table->string('worker_id')->nullable();
            $table->string('town')->default('Colombo');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('demo_stores');
        Schema::table('users', fn (Blueprint $table) => $table->dropColumn(['demo_id', 'role', 'worker_id', 'town']));
    }
};
