/*
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#include <string.h>

#include "libavutil/avstring.h"
#include "libavutil/pixdesc.h"
#include "libavfilter/buffersink.h"

#include "ffmpeg.h"

static int nb_hw_devices;
static HWDevice **hw_devices;

static HWDevice *hw_device_get_by_type(enum AVHWDeviceType type)
{
    HWDevice *found = NULL;
    int i;
    for (i = 0; i < nb_hw_devices; i++) {
        if (hw_devices[i]->type == type) {
            if (found)
                return NULL;
            found = hw_devices[i];
        }
    }
    return found;
}

HWDevice *hw_device_get_by_name(const char *name)
{
    int i;
    for (i = 0; i < nb_hw_devices; i++) {
        if (!strcmp(hw_devices[i]->name, name))
            return hw_devices[i];
    }
    return NULL;
}

static int hwaccel_retrieve_data(AVCodecContext *avctx, AVFrame *input)
{
    InputStream *ist = avctx->opaque;
    AVFrame *output = NULL;
    enum AVPixelFormat output_format = ist->hwaccel_output_format;
    int err;

    if (input->format == output_format) {
        // Nothing to do.
        return 0;
    }

    output = av_frame_alloc();
    if (!output)
        return AVERROR(ENOMEM);

    output->format = output_format;

    err = av_hwframe_transfer_data(output, input, 0);
    if (err < 0) {
        av_log(avctx, AV_LOG_ERROR, "Failed to transfer data to "
               "output frame: %d.\n", err);
        goto fail;
    }

    err = av_frame_copy_props(output, input);
    if (err < 0) {
        av_frame_unref(output);
        goto fail;
    }

    av_frame_unref(input);
    av_frame_move_ref(input, output);
    av_frame_free(&output);

    return 0;

fail:
    av_frame_free(&output);
    return err;
}

int hwaccel_decode_init(AVCodecContext *avctx)
{
    InputStream *ist = avctx->opaque;

    ist->hwaccel_retrieve_data = &hwaccel_retrieve_data;

    return 0;
}

int hw_device_setup_for_filter(FilterGraph *fg)
{
    HWDevice *dev;
    int i;

    // Pick the last hardware device if the user doesn't pick the device for
    // filters explicitly with the filter_hw_device option.
    if (filter_hw_device)
        dev = filter_hw_device;
    else if (nb_hw_devices > 0) {
        dev = hw_devices[nb_hw_devices - 1];

        if (nb_hw_devices > 1)
            av_log(NULL, AV_LOG_WARNING, "There are %d hardware devices. device "
                   "%s of type %s is picked for filters by default. Set hardware "
                   "device explicitly with the filter_hw_device option if device "
                   "%s is not usable for filters.\n",
                   nb_hw_devices, dev->name,
                   av_hwdevice_get_type_name(dev->type), dev->name);
    } else
        dev = NULL;

    if (dev) {
        for (i = 0; i < fg->graph->nb_filters; i++) {
            fg->graph->filters[i]->hw_device_ctx =
                av_buffer_ref(dev->device_ref);
            if (!fg->graph->filters[i]->hw_device_ctx)
                return AVERROR(ENOMEM);
        }
    }

    return 0;
}